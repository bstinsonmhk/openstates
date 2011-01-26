from __future__ import with_statement

import urlparse
import datetime

from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import xlrd
import scrapelib
import lxml.etree


class OHBillScraper(BillScraper):
    state = 'oh'

    def scrape(self, chamber, session):
        if int(session) < 128:
            raise NoDataForPeriod(session)

        base_url = 'http://www.lsc.state.oh.us/status%s/' % session

        bill_types = {'lower': ['hb', 'hjr', 'hcr'],
                      'upper': ['sb', 'sjr', 'scr']}

        for bill_type in bill_types[chamber]:
            url = base_url + '%s.xls' % bill_type

            try:
                fname, resp = self.urlretrieve(url)
            except scrapelib.HTTPError:
                # if there haven't yet been any bills of a given type
                # then the excel url for that type will 404
                continue

            sh = xlrd.open_workbook(fname).sheet_by_index(0)

            for rownum in range(1, sh.nrows):
                bill_id = '%s %s' % (bill_type.upper(), rownum)
                bill_title = str(sh.cell(rownum, 3).value)
                bill = Bill(session, chamber, bill_id, bill_title)
                bill.add_source(url)
                bill.add_sponsor('primary', str(sh.cell(rownum, 1).value))

                # add cosponsor
                if sh.cell(rownum, 2).value:
                    bill.add_sponsor('cosponsor',
                                     str(sh.cell(rownum, 2).value))

                actor = ""

                # Actions start column after bill title
                for colnum in range(4, sh.ncols - 1):
                    action = str(sh.cell(0, colnum).value)
                    cell = sh.cell(rownum, colnum)
                    date = cell.value

                    if len(action) != 0:
                        if action.split()[0] == 'House':
                            actor = "lower"
                        elif action.split()[0] == 'Senate':
                            actor = "upper"
                        elif action.split()[-1] == 'Governor':
                            actor = "executive"
                        elif action.split()[0] == 'Gov.':
                            actor = "executive"
                        elif action.split()[-1] == 'Gov.':
                            actor = "executive"

                    if action in ('House Intro. Date', 'Senate Intro. Date'):
                        atype = ['bill:introduced']
                        action = action.replace('Intro. Date', 'Introduced')
                    elif action == '3rd Consideration':
                        atype = ['bill:reading:3']
                    elif action == 'Sent to Gov.':
                        atype = ['governor:received']
                    elif action == 'Signed By Governor':
                        atype = ['governor:signed']
                    else:
                        atype = ['other']

                    if type(date) == float:
                        date = str(xlrd.xldate_as_tuple(date, 0))
                        date = datetime.datetime.strptime(
                            date, "(%Y, %m, %d, %H, %M, %S)")
                        bill.add_action(actor, action, date, type=atype)

                self.scrape_votes(bill, bill_type, rownum, session)
                self.save_bill(bill)

    def scrape_votes(self, bill, bill_type, number, session):
        vote_url = ('http://www.legislature.state.oh.us/votes.cfm?ID=' +
                    session + '_' + bill_type + '_' + str(number))

        with self.urlopen(vote_url) as page:
            page = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

            for jlink in page.xpath("//a[contains(@href, 'JournalText')]"):
                date = datetime.datetime.strptime(jlink.text,
                                                  "%m/%d/%Y").date()

                details = jlink.xpath("string(../../../td[2])")

                chamber = details.split(" - ")[0]
                if chamber == 'House':
                    chamber = 'lower'
                elif chamber == 'Senate':
                    chamber = 'upper'
                else:
                    raise ScrapeError("Bad chamber: %s" % chamber)

                motion = details.split(" - ")[1].split("\n")[0].strip()

                vote_row = jlink.xpath("../../..")[0].getnext()

                yea_div = vote_row.xpath(
                    "td/font/div[contains(@id, 'Yea')]")[0]
                yeas = []
                for td in yea_div.xpath("table/tr/td"):
                    name = td.xpath("string()")
                    if name:
                        yeas.append(name)

                no_div = vote_row.xpath(
                    "td/font/div[contains(@id, 'Nay')]")[0]
                nays = []
                for td in no_div.xpath("table/tr/td"):
                    name = td.xpath("string()")
                    if name:
                        nays.append(name)

                yes_count = len(yeas)
                no_count = len(nays)

                vote = Vote(chamber, date, motion, yes_count > no_count,
                            yes_count, no_count, 0)

                for yes in yeas:
                    vote.yes(yes)
                for no in nays:
                    vote.no(no)

                bill.add_vote(vote)
