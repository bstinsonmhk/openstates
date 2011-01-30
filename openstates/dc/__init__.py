import datetime

metadata = dict(
    name='District of Columbia',
    abbreviation='dc',
    legislature_name='Council of the District of Columbia',
#    lower_chamber_name='n/a',
    upper_chamber_name='Council',
#    lower_chamber_title='n/a',
    upper_chamber_title='Councilmember',
#    lower_chamber_term=2,
    upper_chamber_term=2,
    terms=[
        {'name': '2005-2006', 'sessions': ['16'],
         'start_year': 2005, 'end_year': 2006},
        {'name': '2007-2008', 'sessions': ['17'],
         'start_year': 2007, 'end_year': 2008},
        {'name': '2009-2010', 'sessions': ['18'],
         'start_year': 2009, 'end_year': 2010},
        {'name': '2011-2012', 'sessions': ['19'],
         'start_year': 2010, 'end_year': 2012},
        ],
    sesssion_details={
#        '18': {'start_date': datetime.date(2001,1,24) },
    }
)

# legislators
    # http://www.dccouncil.washington.dc.us/aboutthecouncil
    # table#PageDataList has the members

