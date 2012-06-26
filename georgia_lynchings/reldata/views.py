from collections import defaultdict, OrderedDict
import json

from django.core.urlresolvers import reverse
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render

from georgia_lynchings.events.models import SemanticTriplet
from georgia_lynchings.lynchings.models import Story
from georgia_lynchings.reldata.models import Relationship

FILTER_FIELDS = ['subject_gender', 'subject_race',
                 'object_gender', 'object_race']

def graph(request):
    '''Display a force-directed graph showing relationships between types of
    people.
    '''
    data_urls = {
        'triples': reverse('relations:graph_triple_data'),
    }
    data_name = request.GET.get('source', None)
    data_url = data_urls.get(data_name, reverse('relations:graph_data'))
    event_url = reverse('relations:event_lookup')

    filters = []
    for field in FILTER_FIELDS:
        field_name = field.replace('_', ' ')
        value_data = Relationship.objects.values(field).annotate(n=Count(field))
        values = [v[field] for v in value_data]
        filters.append((field_name, field, sorted(values)))
    return render(request, 'reldata/graph.html', {
            'data_url': data_url,
            'event_url': event_url,
            'filters': filters,
        })

def wordcloud(request):
    rels = Relationship.objects.exclude(subject_adjective="").\
    values('subject_adjective').annotate(Count('subject_adjective'))
    word_list = [{'word': rel['subject_adjective'], 'count': rel['subject_adjective__count']}
    for rel in rels]

    return render(request, 'reldata/wordle.html', {
        'word_list': word_list,
    })


class RelationsCollection(object):
    '''A collection for managing graph data (nodes and links)'''

    def __init__(self):
        self.nodes = OrderedDict()
        self.links = defaultdict(int)

    def add_relationship_object(self, rel):
        '''Add all nodes and links for a single
        :class:`~georgia_lynchings.reldata.models.Relationship to the
        collection.
        '''
        if rel.subject_desc and rel.object_desc:
            self.add_single_relationship(rel.subject_desc, rel.object_desc)

    def add_single_relationship(self, subj, obj):
        '''Add the nodes and links for a single subject-object pair to the
        collection.
        '''
        subj_node = (self.get_node_id(subj), subj)
        obj_node = (self.get_node_id(obj), obj)

        # we're treating links as undirected for now. order them so that
        # (a, b) and (b, a) are counted together.
        if subj_node < obj_node:
            endpoints = (subj_node, obj_node)
        else:
            endpoints = (obj_node, subj_node)

        self.links[endpoints] += 1

    def get_node_id(self, name):
        '''Get a unique integer id for the node with the given name,
        creating one sequentially if necessary. Increment reference count.''' 
        if name in self.nodes:
            val = self.nodes[name]
            val['count'] += 1
        else:
            num = len(self.nodes)
            val = {'num': num, 'count': 1}
            self.nodes[name] = val
        return val['num']

    def as_graph_data(self):
        '''Translate nodes and links in this collection into lists and
        dictionaries for easy serialization.

        NB: This data is handled directly by the graph template js logic. If
        we change it here, then we probably need to change it there, too.
        '''
        return {
            'nodes': [{'name': name,
                       'value': node['count']}
                      for name, node in self.nodes.iteritems()],
            'links': [{'source': key[0][0],
                       'source_name': key[0][1],
                       'target': key[1][0],
                       'target_name': key[1][1],
                       'value': val}
                      for (key, val) in self.links.iteritems()],
        }
        

def graph_data(request):
    '''Collect data for a (force-directed) relationship graph from available
    :class:`~georgia_lynchings.reldata.models.Relationship` data.
    '''
    rel_qs = Relationship.objects.all()
    for field in FILTER_FIELDS:
        value = request.GET.get(field, '')
        if value:
            rel_qs = rel_qs.filter(**{field: value})

    rels = RelationsCollection()
    for rel in rel_qs:
        rels.add_relationship_object(rel)

    result = rels.as_graph_data()
    result_s = json.dumps(result)
    return HttpResponse(result_s, content_type='application/json')


def graph_triple_data(request):
    '''Collect data for a (force-directed) relationship graph from available
    :class:`~georgia_lynchings.event.models.SemanticTriplet` data.
    '''
    rels = RelationsCollection()
    for subj, obj in triple_subject_object_pairs():
        if subj.actor_name and obj.actor_name:
            rels.add_single_relationship(subj.actor_name, obj.actor_name)

    result = rels.as_graph_data()
    result_s = json.dumps(result)
    return HttpResponse(result_s, content_type='application/json')

def cloud_data(request):
    '''
    Generates json data for the wordcloud view.
    '''
    rels = Relationship.objects.exclude(subject_adjective="").\
        values('subject_adjective').annotate(Count('subject_adjective'))
    data = [{'word': rel['subject_adjective'], 'count': rel['subject_adjective__count']}
        for rel in rels]
    return HttpResponse(json.dumps(data), content_type='application/json')


def triple_subject_object_pairs():
    '''Generate all subject-object pairs of all
    :class:`~georgia_lynchings.event.models.SemanticTriplet` objects.
    '''
    FIELDS = [
        'participant_s__individuals__actor_name',
        'participant_o__individuals__actor_name',
        ]
    triplets = SemanticTriplet.objects.fields(*FIELDS).all()
    for tr in triplets:
        for ps in tr.participant_s:
            for po in tr.participant_o:
                for s in ps.individuals:
                    for o in po.individuals:
                        yield (s, o)


def event_lookup(request):
    if 'participant' not in request.GET:
        msg = "Event search requires search terms. Current recognized " + \
              "search terms are: participant"
        return HttpResponseBadRequest(msg)

    qs = Story.objects.distinct()

    participant = request.GET.get('participant')
    if participant:
        qs = qs.filter(Q(relationship__subject_desc=participant) |
                       Q(relationship__object_desc=participant))

    # TODO: tons of queries here. ought to find a way to do the bulk of this
    # work in a single query. it should be possible--maybe with
    # annotations/aggregations? in particular, if a relationship includes
    # the query term twice, the output needs to count that relationship
    # twice in the appearances count.
    data = [{ 'url': s.get_absolute_url(),
              'name': unicode(s),
              'appearances': len(s.relationship_set.filter(subject_desc=participant)) + \
                             len(s.relationship_set.filter(object_desc=participant))
            } for s in qs]
    sorted_data = sorted(data, key=lambda s:s['appearances'], reverse=True)
    return HttpResponse(json.dumps(sorted_data),
                        content_type='application/json')
