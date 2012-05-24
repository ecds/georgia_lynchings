import json

from django.http import Http404, HttpResponse
from django.db.models import Count
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse

from georgia_lynchings.lynchings.models import Story, Person, Lynching, County, Accusation

def story_detail(request, story_id):
    """
    Renders a detailed view for a specific story_id.
    """
    story = get_object_or_404(Story, pk=story_id)


    return render(request, 'lynchings/details.html',{
        'story': story,
        })

def story_list(request):
    """
    Renders a simple list of lynching stories.
    """
    story_list = Story.objects.all()

    return render(request, 'lynchings/list_events.html', {
        'story_list': story_list,
    })

def story_list_by_accusation(request, accusation_id):
    """
    Returns a list of lynchings based on the accusations that lead to the event.
    """
    story_list = Story.objects.filter(lynching__alleged_crime__id=accusation_id)

    return render(request, 'lynchings/list_events.html', {
        'story_list': story_list,
    })

def alleged_crimes_list(request):
    """
    Returns a list of alleged crimes with counts for number of related lynhcings.
    """
    accusation_list = Accusation.objects.annotate(stories=Count('lynching__pk'))

    return render(request, 'lynchings/alleged_crimes.html', {
        'accusation_list': accusation_list,
    })

def timemap(request):
    return render(request, 'lynchings/timemap.html')

def timemap_data(request):
    """
    Renders a json return for use with timemap.
    """
    story_data = [_story_timemap_data(story) for story in Story.objects.all()]
    json_literal = [d for d in story_data
                    if d.get('start', None) and
                       d.get('point', None)]

    return HttpResponse(json.dumps(json_literal, indent=4),
        mimetype='application/json')

def _story_timemap_data(story):
    """
    Formats a datapoint for an individual lynching story.

    """
    data = {
        'title': u'%s' % story,
        'options': {
            'detail_link': reverse('lynchings:story_detail', args=[story.id,]),
            }
    }
    try:
        county = story.county_list[0]
        if county:
            data['options']['county'] = county.label
            data['point'] = {
                'lat': county.latitude,
                'lon': county.longitude,
            }
    except IndexError:
        pass

    try:
        accusations = [lynching.alleged_crime.label for lynching in story.lynching_set.all()
                if lynching.alleged_crime]
        data['options']['alleged_crime'] = accusations[0] # all crimes are the same or none.
    except IndexError:
        pass

    try:
        date = [lynching.date for lynching in story.lynching_set.all() if lynching.date][0]
        # strftime can't reliably do dates before 1900
        date_str = "%04d-%02d-%02d" % (date.year, date.month, date.day)
        data['start'] = date_str
        data['options']['date'] = date_str
    except IndexError:
        pass

    return data