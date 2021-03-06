import string
from model_mommy import mommy
from datetime import datetime
from django_rq import job
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.test.client import RequestFactory
from django.contrib.auth.models import User
from django.utils import timezone
from dateutil.parser import parse as extract_date
from django.conf import settings
from survey.models import (InterviewerAccess, ODKAccess, USSDAccess, Interview, Interviewer, QuestionSetChannel,
                           EnumerationArea, Survey, SurveyAllocation, Question, QuestionSet, Batch, BatchQuestion,
                           QuestionOption)
from survey.forms.question import get_question_form
# import all question types
from survey.models import (Answer, NumericalAnswer, TextAnswer, MultiChoiceAnswer, MultiSelectAnswer, GeopointAnswer,
                           ImageAnswer, AudioAnswer, VideoAnswer, DateAnswer, AutoResponse)
from survey.utils.decorators import static_var
from survey.tests.base_test import BaseTest
from survey.forms.answer import SurveyAllocationForm, AddMoreLoopForm
from .survey_base_test import SurveyBaseTest
from survey.utils.views_helper import activate_super_powers


class InterviewsTest(SurveyBaseTest):

    def test_name(self):
        interview = self.interview
        self.assertEquals(str(interview), '%s: %s' % (interview.id, interview.question_set.name))

    def test_is_closed(self):
        self.assertEquals(self.interview.closure_date is not None, self.interview.is_closed())

    def test_interview_qset_gives_property_maps_to_correct_type(self):
        self.assertEquals(self.qset.id, self.interview.qset.id)
        self.assertEquals(self.qset.__class__, self.interview.qset.__class__)

    def test_interview_is_considered_stared_when_last_question_is_not_none(self):
        self.assertEquals(self.interview.last_question, None)
        self.assertFalse(self.interview.has_started)

    def test_question_text_is_given_when_no_response_is_supplied(self):
        self._create_ussd_non_group_questions(self.qset)
        interview = self.interview
        first_question = interview.question_set.start_question
        # confirm if its the Numerical answer
        self.assertEquals(first_question.answer_type, NumericalAnswer.choice_name())
        # interview has not started
        self.assertEquals(interview.has_started, False)
        self.assertEquals(Answer.objects.count(), 0)
        response = interview.respond()      # first question is numerical
        self.assertEquals(response, first_question.text)

    def test_last_question_is_updated_after_response(self):
        self._create_ussd_non_group_questions(self.qset)
        interview = self.interview
        first_question = interview.question_set.start_question
        # confirm if its the Numerical answer
        self.assertEquals(first_question.answer_type, NumericalAnswer.choice_name())
        response = interview.respond()
        interview.refresh_from_db()
        self.assertEquals(interview.has_started, True)
        self.assertEquals(interview.last_question.id, first_question.id)

    def _validate_response(self, question, answer, interview=None):
        if interview is None:
            interview = self.interview
        answer_count = Answer.objects.count()
        questions = self.qset.flow_questions
        interview.respond(reply=answer, answers_context={})
        interview.refresh_from_db()
        self.assertEquals(Answer.objects.count(), answer_count+1)
        next_question = question.next_question(answer)
        # just confirm text value of this answer was saved
        self.assertTrue(interview.get_answer(question), str(answer))
        question = Question.get(id=question.id)
        # next test is valid
        if questions.index(question) < len(questions) - 1:
            self.assertEquals(next_question.id, questions[questions.index(question)+1].id)
            self.assertEquals(next_question.id, interview.last_question.id)

    def test_interview_response_flow(self):
        self._create_ussd_non_group_questions(self.qset)
        interview = self.interview
        self._try_interview(interview)

    def _try_interview(self, interview):
        first_question = interview.question_set.start_question
        response = interview.respond()      # first question is numerical
        self.assertEquals(response, first_question.text)
        self._validate_response(first_question, 1, interview=interview)      # numerical question
        self._validate_response(self.qset.flow_questions[1], 'Howdy', interview=interview) # text question
        self._validate_response(self.qset.flow_questions[2], 'N', interview=interview) # Multichoice
        # auto response is internally an integer answer only that its generated by code (but outside models)
        self._validate_response(self.qset.flow_questions[3], 1, interview=interview)  # Auto response
        # now assert that the interview is closed.
        self.assertTrue(interview.is_closed())

    def test_interviews_belonging_to_a_survey(self):
        self._create_ussd_non_group_questions(self.qset)
        interview = mommy.make(Interview, interviewer=self.interviewer, survey=self.survey, ea=self.ea,
                               interview_channel=self.access_channel, question_set=self.qset)
        self._try_interview(interview)
        self.assertEquals(Interview.interviews(self.survey).exclude(survey=self.survey).count(), 0)

    def test_interviews_in_a_location(self):
        self._create_ussd_non_group_questions(self.qset)
        location1 = self.ea.locations.first()
        interview = mommy.make(Interview, interviewer=self.interviewer, survey=self.survey, ea=self.ea,
                               interview_channel=self.access_channel, question_set=self.qset)
        self._try_interview(interview)
        interview = mommy.make(Interview, interviewer=self.interviewer, survey=self.survey, ea=self.ea,
                               interview_channel=self.access_channel, question_set=self.qset)
        self._try_interview(interview)
        self.assertEquals(Interview.interviews_in(location1, include_self=True).count(), Interview.objects.count())
        self.assertEquals(Interview.interviews_in(location1, survey=self.survey, include_self=True).count(),
                          Interview.objects.count())
        # test another location doesnt have any interviews
        location2 = EnumerationArea.objects.exclude(locations__in=self.ea.locations.all()).first().locations.first()
        self.assertEquals(Interview.interviews_in(location2, include_self=True).count(), 0)
        self.assertEquals(Interview.interviews_in(location2, survey=self.survey, include_self=True).count(), 0)

    def _load_other_client(self):
        self.client = Client()
        User.objects.create_user(username='useless', email='demo3@kant.com', password='I_Suck')
        user = User.objects.create_user('demo13', 'demo3@kant.com', 'demo13')
        self.assign_permission_to(user, 'can_have_super_powers')
        self.assign_permission_to(user, 'can_view_users')
        self.client.login(username='demo13', password='demo13')
        return user

    def test_bulk_answer_questions(self):
        self._create_ussd_non_group_questions(self.qset)
        answers = []
        n_quest = Question.objects.get(answer_type=NumericalAnswer.choice_name())
        t_quest = Question.objects.get(answer_type=TextAnswer.choice_name())
        m_quest = Question.objects.get(answer_type=MultiChoiceAnswer.choice_name())
        # first is numeric, then text, then multichioice
        answers = [{n_quest.id: 1, t_quest.id: 'Hey Man', m_quest.id: 'Y'},
                   {n_quest.id: 5, t_quest.id: 'Hey Boy', m_quest.id: 'Y'},
                   {n_quest.id: 15, t_quest.id: 'Hey Girl!', m_quest.id: 'N'},
                   {n_quest.id: 15, t_quest.id: 'Hey Part!'}
                   ]
        question_map = {n_quest.id: n_quest, t_quest.id: t_quest, m_quest.id: m_quest}
        interview = self.interview
        Interview.save_answers(self.qset, self.survey, self.ea,
                               self.access_channel, question_map, answers)
        # confirm that 11 answers has been created
        self.assertEquals(NumericalAnswer.objects.count(), 4)
        self.assertEquals(TextAnswer.objects.count(), 4)
        self.assertEquals(MultiChoiceAnswer.objects.count(), 3)
        self.assertEquals(TextAnswer.objects.first().to_text().lower(), 'Hey Man'.lower())
        self.assertEquals(MultiChoiceAnswer.objects.first().as_text.lower(), 'Y'.lower())
        self.assertEquals(MultiChoiceAnswer.objects.first().as_value, str(QuestionOption.objects.get(text='Y').order))
        # now test wipe data
        request = RequestFactory().get('.')
        request.user = self._load_other_client()
        activate_super_powers(request)
        url = reverse('wipe_survey_data', args=(self.survey.id,))
        answer_count = Answer.objects.count()
        self.assertTrue(answer_count > 0)
        response = self.client.get(url)
        self.assertEquals(Answer.objects.count(), 0)

    def test_respond_on_closed_interview(self):
        self.interview.closure_date = timezone.now()
        self.interview.save()
        self.assertEquals(self.interview.respond(), None)

    def test_respond_start_question_interview(self):
        self._create_ussd_group_questions()
        self.assertEquals(self.interview.respond(),
                          self.qset.g_first_question.display_text(channel=ODKAccess.choice_name()))


class InterviewsTestExtra(SurveyBaseTest):
    def test_first_question_is_loop_first(self):
        self._create_ussd_group_questions()
        # test first question is group first
        self.assertEquals(self.interview.respond(),
                          self.qset.g_first_question.display_text(channel=ODKAccess.choice_name(), context={}))
        # test running again gives same results
        self.assertEquals(self.interview.respond(),
                          self.qset.g_first_question.display_text(channel=ODKAccess.choice_name(), context={}))

    def test_interviews_in_exclude_self(self):
        location = self.ea.locations.first()
        interviews = Interview.interviews_in(location.parent)
        self.assertTrue(interviews.filter(id=self.interview.id).exists())

    def test_answers_unicode_rep(self):
        self._create_ussd_non_group_questions()
        n_question = Question.objects.filter(answer_type=NumericalAnswer.choice_name()).first()
        answer = NumericalAnswer.create(self.interview, n_question, 1)
        self.assertEquals(str(answer.as_text), unicode(answer))
        # test update (since numeric makes use of thr parent implementation)
        answer.update(2)
        self.assertEquals(answer.as_value, 2)
        # just test to label also :)
        self.assertEquals(answer.to_label(), 2)
        #test to pretty_print
        self.assertEquals(str(answer.pretty_print()), '2')

    def test_get_answer_class_with_doesnt_exist(self):
        self.assertRaises(ValueError, Answer.get_class, 'Fake_Anwer')

    def _prep_answers(self):
        self._create_test_non_group_questions(self.qset)
        answers = []
        n_quest = Question.objects.get(answer_type=NumericalAnswer.choice_name())
        t_quest = Question.objects.get(answer_type=TextAnswer.choice_name())
        m_quest = Question.objects.get(answer_type=MultiChoiceAnswer.choice_name())
        # first is numeric, then text, then multichioice
        answers = [{n_quest.id: 1, t_quest.id: 'Hey Man', m_quest.id: 'Y'},
                   {n_quest.id: 5, t_quest.id: 'Our Hey Boy', m_quest.id: 'Y'},
                   {n_quest.id: 27, t_quest.id: 'Hey Girl!', m_quest.id: 'N'},
                   {n_quest.id: 12, t_quest.id: 'Hey Raster!', m_quest.id: 'N'},
                   {n_quest.id: 19, t_quest.id: 'This bad boy'}
                   ]
        question_map = {n_quest.id: n_quest, t_quest.id: t_quest, m_quest.id: m_quest}
        interview = self.interview
        interviews = Interview.save_answers(self.qset, self.survey, self.ea,
                                            self.access_channel, question_map, answers)
        # confirm that 11 answers has been created
        self.assertEquals(NumericalAnswer.objects.count(), 5)
        self.assertEquals(TextAnswer.objects.count(), 5)
        self.assertEquals(MultiChoiceAnswer.objects.count(), 4)
        self.assertEquals(TextAnswer.objects.first().to_text().lower(), 'Hey Man'.lower())
        self.assertEquals(MultiChoiceAnswer.objects.first().as_text.lower(), 'Y'.lower())
        multichoice = MultiChoiceAnswer.objects.first()
        self.assertEquals(multichoice.as_value,
                          str(QuestionOption.objects.get(text='Y', question=multichoice.question).order))
        return Interview.objects.filter(id__in=[i.id for i in interviews])

    def test_answer_qs_filters(self):
        interviews = self._prep_answers()
        fetched_interviews = Answer.fetch_contains('answer__as_value', 'Hey', qs=interviews)    # 4 intervies meet this
        self.assertEquals(fetched_interviews.count(), 4)
        fetched_interviews = Answer.fetch_starts_with('answer__as_value', 'Hey', qs=interviews)  # 3 intervies meet this
        self.assertEquals(fetched_interviews.count(), 3)
        fetched_interviews = Answer.fetch_ends_with('answer__as_value', 'boy', qs=interviews)  # 2 intervies meet this
        self.assertEquals(fetched_interviews.count(), 2)
        fetched_answers = Answer.fetch_contains('as_value', 'boy')  # 2 intervies meet this
        self.assertEquals(fetched_answers.count(), 2)
        fetched_answers = Answer.fetch_starts_with('as_value', 'This')  # 1 intervies meet this
        self.assertEquals(fetched_answers.count(), 1)
        fetched_answers = Answer.fetch_ends_with('as_value', 'boy')  # 2 intervies meet this
        self.assertEquals(fetched_answers.count(), 2)

    def test_odk_answer_methods(self):
        # test odk contain
        path = '/qset/qset1/surveyQuestions/q1'
        value = 'me doing somthing'
        self.assertEquals(Answer.odk_contains(path, value), "regex(%s, '.*(%s).*')" % (path, value))
        self.assertEquals(Answer.odk_starts_with(path, value), "regex(%s, '^(%s).*')" % (path, value))
        self.assertEquals(Answer.odk_ends_with(path, value), "regex(%s, '.*(%s)$')" % (path, value))
        value = 4
        upperlmt = 10
        self.assertEquals(Answer.odk_greater_than(path, value), "%s &gt; '%s'" % (path, value))
        self.assertEquals(Answer.odk_less_than(path, value), "%s &lt; '%s'" % (path, value))
        self.assertEquals(Answer.odk_between(path, value, upperlmt),
                          "(%s &gt; '%s') and (%s &lt;= '%s')" % (path, value, path, upperlmt))
        self.assertEquals(NumericalAnswer.odk_less_than(path, value), "%s &lt; %s" % (path, value))
        self.assertEquals(NumericalAnswer.odk_between(path, value, upperlmt),
                          "(%s &gt; %s) and (%s &lt;= %s)" % (path, value, path, upperlmt))
        value = '20-07-2017'
        self.assertEquals(DateAnswer.odk_greater_than(path, value),
                          "%s &gt; %s" % (path, DateAnswer.to_odk_date(value)))
        self.assertEquals(DateAnswer.odk_less_than(path, value),
                          "%s &lt; %s" % (path, DateAnswer.to_odk_date(value)))
        upperlmt = '25-08-2017'
        self.assertEquals(DateAnswer.odk_between(path, value, upperlmt),
                          "(%s &gt; %s) and (%s &lt;= %s)" % (path,
                                                              DateAnswer.to_odk_date(value),
                                                              path, DateAnswer.to_odk_date(upperlmt)))

    def test_answer_value_methods(self):
        value = 'me doing somthing'
        test_answer1 = 'nothing good'
        self.assertFalse(Answer.equals(test_answer1, value))
        self.assertTrue(Answer.equals(value, value))
        self.assertTrue(Answer.starts_with(value, 'me d'))
        self.assertFalse(Answer.ends_with(value, 'no thing'))
        self.assertTrue(Answer.ends_with(value, 'somthing'))
        self.assertFalse(Answer.greater_than(5, 9))
        self.assertTrue(Answer.greater_than(9, 5))
        self.assertTrue(Answer.less_than(5, 9))
        self.assertFalse(Answer.less_than(9, 5))
        self.assertFalse(Answer.between(9, 5, 7))
        self.assertTrue(Answer.between(9, 5, 11))
        self.assertTrue(Answer.passes_test('17 > 10'))
        self.assertFalse(NumericalAnswer.greater_than(5, 9))
        self.assertTrue(NumericalAnswer.greater_than(9, 5))
        self.assertTrue(NumericalAnswer.less_than(5, 9))
        self.assertFalse(NumericalAnswer.less_than(9, 5))
        self.assertFalse(NumericalAnswer.between(9, 5, 7))
        self.assertTrue(NumericalAnswer.between(9, 5, 11))
        self.assertFalse(TextAnswer.equals(test_answer1, value))
        self.assertTrue(TextAnswer.equals(value, value))
        self.assertFalse(MultiChoiceAnswer.equals(test_answer1, value))
        self.assertTrue(MultiChoiceAnswer.equals(value, value))
        self.assertFalse(MultiSelectAnswer.equals(test_answer1, value))
        self.assertTrue(MultiSelectAnswer.equals(value, value))
        self.assertFalse(DateAnswer.greater_than('12-09-2017', '12-09-2017'))
        self.assertTrue(DateAnswer.greater_than('13-09-2017', '12-09-2017'))
        self.assertFalse(DateAnswer.less_than('18-09-2017', '12-09-2017'))
        self.assertTrue(DateAnswer.less_than('13-09-2017', '17-09-2017'))
        self.assertFalse(DateAnswer.between('18-09-2017', '12-09-2017',  '16-09-2017'))
        self.assertTrue(DateAnswer.between('14-09-2017', '12-09-2017',  '16-09-2017'))

    def test_other_answer_methods(self):
        interviews = self._prep_answers()
        m_answer = MultiChoiceAnswer.objects.last()
        self.assertEqual(m_answer.pretty_print(as_label=False), m_answer.value.text)
        self.assertEqual(m_answer.pretty_print(as_label=True), m_answer.value.order)
        multiselect_question = Question.objects.filter(answer_type=MultiSelectAnswer.choice_name()).last()
        MultiSelectAnswer.create(self.interview, multiselect_question, 'Y N')
        self.assertEqual(MultiSelectAnswer.objects.count(), 1)
        multiselect = MultiSelectAnswer.objects.last()
        self.assertEqual(multiselect.to_text(), ' and '.join(['Y', 'N']))
        self.assertEqual(multiselect.to_label(), ' and '.join(['1', '2']))
        self.assertEqual(multiselect.pretty_print(as_label=False), multiselect.to_text())
        self.assertEqual(multiselect.pretty_print(as_label=True), multiselect.to_label())






