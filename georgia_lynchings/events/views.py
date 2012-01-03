import logging
from django.shortcuts import render
from georgia_lynchings.events.models import MacroEvent, get_events_by_locations, get_events_by_times, get_all_macro_events

logger = logging.getLogger(__name__)

def articles(request, row_id):
    '''
    List all articles for a
    :class:`~georgia_lynchings.events.models.MacroEvent`.
    
    :param row_id: the numeric identifier for the 
                   :class:`~georgia_lynchings.events.models.MacroEvent`.
    '''
    event = MacroEvent(row_id)
    resultSet = event.get_articles()
    if resultSet:   title = resultSet[0]['melabel']['value']
    else:   title = "No records found"    
    return render(request, 'events/articles.html',
                  {'resultSet': resultSet, 'row_id':row_id, 'title':title})    


def locations(request):
    '''List all events, ordered by their location.'''

    results = get_events_by_locations()
    return render(request, 'events/locations.html',
                  {'results': results})
                  
def times(request):
    '''List all events, provide the date range as mindate and maxdate.'''

    results = get_events_by_times()
    if results:   title = "%d Macro Events" % len(results)
    else:   title = "No records found"      
    return render(request, 'events/times.html',
                  {'results': results, 'title':title}) 
                  
def macro_events(request):
    '''List all macro events, provide article count.'''

    results = get_all_macro_events()
    if results:   title = "%d Macro Events" % len(results)
    else:   title = "No records found"      
    return render(request, 'events/macro_events.html',
                  {'results': results, 'title':title}) 
