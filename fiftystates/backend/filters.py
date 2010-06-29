import nltk
import name_tools

from fiftystates.backend.utils import timestamp_to_dt

from nimsp import nimsp, NimspApiError
from votesmart import votesmart, VotesmartApiError

from saucebrush.filters import Filter, ConditionalFilter, FieldFilter


class Keywordize(Filter):
    def __init__(self, field_name, new_field):
        super(Keywordize, self).__init__()
        self._field_name = field_name
        self._new_field = new_field
        self._stemmer = nltk.stem.porter.PorterStemmer()
        self._stop_words = nltk.corpus.stopwords.words()

    def process_record(self, record):
        sents = nltk.tokenize.sent_tokenize(record[self._field_name])

        words = []
        for sent in sents:
            words.extend(nltk.tokenize.word_tokenize(sent))

        keywords = set([self._stemmer.stem(word.lower()) for word in words if
                        (word.isalpha() or word.isdigit()) and
                        word.lower() not in self._stop_words])

        record[self._new_field] = sorted(list(keywords))

        return record


class SplitName(Filter):
    def __init__(self, name_field='full_name'):
        super(SplitName, self).__init__()
        self._name_field = name_field

    def process_record(self, record):
        # If the record already has first_name and last_name fields
        # then don't overwrite them.
        try:
            if record['first_name'] and record['last_name']:
                return record
        except KeyError:
            pass

        full_name = record[self._name_field]

        (record['prefixes'], record['first_name'],
         record['last_name'], record['suffixes']) = name_tools.split(full_name)

        return record


class LinkNIMSP(Filter):
    def __init__(self, apikey=None, election_year='2008'):
        super(LinkNIMSP, self).__init__()
        self.election_year = election_year
        if apikey:
            self._apikey = apikey
        else:
            self._apikey = settings.NIMSP_API_KEY
        nimsp.apikey = self._apikey

    def process_record(self, record):
        role = record['roles'][0]

        # NIMSP is picky about name format
        name = record['last_name']
        if 'suffix' in record and record['suffix']:
            name += " " + record['suffix'].replace(".", "")
        name += ", " + record['first_name'].replace(".", "")

        office_id = dict(upper='S00', lower='R00')[role['chamber']]

        try:
            results = nimsp.candidates.list(
                state=role['state'], office=office_id,
                candidate_name=name, year=self.election_year,
                candidate_status='WON')
        except NimspApiError as e:
            print "Failed matching %s" % name
            record['nimsp_candidate_id'] = None
            return record

        if len(results) == 1:
            record['nimsp_candidate_id'] = int(results[0].imsp_candidate_id)
        else:
            record['nimsp_candidate_id'] = None
            print "Too many results for %s" % name

        return record


class LinkVotesmart(Filter):
    def __init__(self, state, apikey=None):
        super(LinkVotesmart, self).__init__()
        if apikey:
            self._apikey = apikey
        else:
            self._apikey = settings.VOTESMART_API_KEY
        votesmart.apikey = self._apikey

        self._officials = {}

        for chamber, office in dict(upper=9, lower=8).items():
            try:
                self._officials[chamber] = (
                    votesmart.officials.getByOfficeState(
                        office, state.upper()))
            except VotesmartApiError:
                self._officials[chamber] = []

    def process_record(self, record):
        role = record['roles'][0]

        for official in self._officials[role['chamber']]:
            if (official.firstName == record['first_name'] and
                official.lastName == record['last_name']):

                record['votesmart_id'] = official.candidateId
                return record

        print "VS - failed match %s" % record['full_name']
        return record


class LegislatorIDValidator(ConditionalFilter):
    validator = True

    def __init__(self):
        super(LegislatorIDValidator, self).__init__()
        self._votesmart_seen = set()
        self._nimsp_seen = set()

    def test_record(self, record):
        votesmart_id = record.get('votesmart_id')
        if votesmart_id:
            if votesmart_id in self._votesmart_seen:
                return False
            self._votesmart_seen.add(votesmart_id)

        nimsp_id = record.get('nimsp_candidate_id')
        if nimsp_id:
            if nimsp_id in self._nimsp_seen:
                return False
            self._nimsp_seen.add(nimsp_id)

        return True


class TimestampToDatetime(FieldFilter):
    def process_field(self, item):
        return timestamp_to_dt(item)