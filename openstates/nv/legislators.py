import re
import urlparse
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.nv.utils import clean_committee_name

import lxml.etree
import urllib

class NVLegislatorScraper(LegislatorScraper):
    state = 'nv'

    def scrape(self, chamber, term_name):
        self.save_errors=False
        year = term_name[0:4]
        if int(year) < 2001:
            raise NoDataForPeriod(year)

        if ((int(year) - 2010) % 2) == 1:
            session = ((int(year) -  2010) / 2) + 76
        elif( ((int(year) - 2010) % 2) == 0) and year >= 2010:
            session = ((int(year) - 2010) / 2) + 26
        else:
            raise NoDataForPeriod(term_name)

        self.scrape_legislators(chamber, session, year, term_name)

    def scrape_legislators(self, chamber, session, year, term_name):

        sessionsuffix = 'th'
        if str(session)[-1] == '1':
            sessionsuffix = 'st'
        elif str(session)[-1] == '2':
            sessionsuffix = 'nd'
        elif str(session)[-1] == '3':
            sessionsuffix = 'rd'

        insert = str(session) + sessionsuffix + str(year)
        if session == 26:
            insert = str(session) + sessionsuffix + str(year) + "Special"

        if chamber == 'upper':
            leg_url = 'http://www.leg.state.nv.us/Session/' + insert  + '/legislators/Senators/slist.cfm'
            num_districts = 22
        elif chamber == 'lower':
            leg_url = 'http://www.leg.state.nv.us/Session/' + insert  + '/legislators/Assembly/alist.cfm'
            num_districts = 43

        with self.urlopen(leg_url) as page:
            page = page.replace("&nbsp;", " ")
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

            #Going through the districts
            for row_index in range(3, num_districts+2):
                print row_index
                namepath = 'string(//table[%s]/tr/td/table[1]/tr/td[2])' % row_index
                last_name = root.xpath(namepath).split()[0]
                last_name = last_name[0 : len(last_name) - 1]
                middle_name = ''

                if len(root.xpath(namepath).split()) == 2:
                    first_name = root.xpath(namepath).split()[1]
                elif len(root.xpath(namepath).split()) == 3:
                    first_name = root.xpath(namepath).split()[1]
                    middle_name = root.xpath(namepath).split()[2]
                elif len(root.xpath(namepath).split()) == 4:
                    first_name = root.xpath(namepath).split()[2]
                    middle_name = root.xpath(namepath).split()[3]
                    last_name = last_name + " " + root.xpath(namepath).split()[1]
                    last_name = last_name[0: len(last_name) - 1]

                if len(middle_name) > 0:
                    full_name = first_name + " " + middle_name + " " + last_name
                else:
                    full_name = first_name + " " + last_name

                partypath = 'string(//table[%s]/tr/td/table[1]/tr/td[3])' % row_index
                party = root.xpath(partypath).split()[-1]
                if party == 'Democrat':
                    party = 'Democratic'

                districtpath = 'string(//table[%s]/tr/td/table[1]/tr/td[4])' % row_index
                district = root.xpath(districtpath)[11: len(root.xpath(districtpath))].strip()
                if district.startswith('No.'):
                    district = district[3:].strip()

                termpath = 'string(//table[%s]/tr/td/table[2]/tr/td[5])' % row_index
                end_date = root.xpath(termpath)[12: 21]
                email = root.xpath(termpath).split()[-1]

                addresspath = 'string(//table[%s]/tr/td/table[2]/tr/td[2])' % row_index
                address = root.xpath(addresspath)

                leg = Legislator(term_name, chamber, district, full_name,
                                 first_name, last_name, middle_name, party,
                                 email=email, address=address)
                leg.add_source(leg_url)
                self.save_legislator(leg)


