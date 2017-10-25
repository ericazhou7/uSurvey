from django.test import TestCase
from survey.models.locations import Location, LocationType
from survey.forms.surveys import SurveyForm
from survey.models import Batch, Interviewer, SurveyAllocation, Backend, EnumerationArea, Question
from survey.models.surveys import Survey
from model_mommy import mommy
from survey.models import (Answer, MultiChoiceAnswer, MultiSelectAnswer, DateAnswer, QuestionFlow,
                           Question, TextArgument, NumericalAnswer, TextAnswer, TemplateOption)
from survey.models import AnswerAccessDefinition, AutoResponse, NumericalAnswer, TextAnswer, \
    MultiChoiceAnswer, MultiSelectAnswer, ImageAnswer, GeopointAnswer, DateAnswer, AudioAnswer, VideoAnswer, \
    USSDAccess, ODKAccess, WebAccess                           
from survey.models.survey_listing import ListingTemplate, ListingQuestion


class SurveyTest(TestCase):

    def test_fields(self):
        survey = Survey()
        fields = [str(item.attname) for item in survey._meta.fields]
        self.assertEqual(10, len(fields))
        for field in ['id','created','modified','name','description','has_sampling','sample_size','listing_form_id','preferred_listing_id','random_sample_label']:
            self.assertIn(field, fields)

    def test_store(self):
        survey = Survey.objects.create(
            name="survey name", description="rajni survey")
        self.failUnless(survey.id)
        self.failUnless(survey.id)
        self.failUnless(survey.created)
        self.failUnless(survey.modified)
        self.assertEquals(10, survey.sample_size)
        self.assertTrue(survey.has_sampling)

    def test_survey_knows_it_is_open(self):
        survey = Survey.objects.create(
            name="survey name", description="rajni survey")
        batch = Batch.objects.create(order=1)
        ea = EnumerationArea.objects.create(name="EA2")
        country = LocationType.objects.create(name="Country", slug="country")
        region = LocationType.objects.create(name="Region", slug="region")
        district = LocationType.objects.create(
            name="District", slug='district')
        uganda = Location.objects.create(name="Uganda", type=country)
        kampala = Location.objects.create(
            name="Kampala", tree_parent=uganda, type=district)
        ea.locations.add(kampala)
        self.investigator = Interviewer.objects.create(name="Investigator",
                                                       ea=ea,
                                                       gender='1', level_of_education='Primary',
                                                       language='Eglish', weights=0)
        survey = Survey.objects.create(
            name="survey name123", description="rajni survey123")
        batch = Batch.objects.create(order=1, survey=survey)
        batch.open_for_location(kampala)
        self.assertTrue(survey.is_open())

    def test_survey_knows_it_is_open_for_investigator_location_if_provided(self):
        survey = Survey.objects.create(
            name="survey name234", description="rajni surve234y")
        ea = EnumerationArea.objects.create(name="EA2")
        country = LocationType.objects.create(name="Country", slug="country")
        region = LocationType.objects.create(name="Region", slug="region")
        district = LocationType.objects.create(
            name="District", slug='district')
        uganda = Location.objects.create(name="Uganda", type=country)
        kampala = Location.objects.create(
            name="Kampala", tree_parent=uganda, type=district)
        ea.locations.add(kampala)
        self.investigator = Interviewer.objects.create(name="Investigator",
                                                       ea=ea,
                                                       gender='1', level_of_education='Primary',
                                                       language='Eglish', weights=0)
        survey = Survey.objects.create(
            name="survey name333", description="rajni survey33333")
        batch = Batch.objects.create(order=1, survey=survey)
        survey_allocation = SurveyAllocation.objects.create(interviewer=self.investigator, survey=survey, allocation_ea=ea, stage=2,
                                                            status=0)
        batch.open_for_location(kampala)
        self.assertTrue(survey.is_open())

    def test_survey_knows_it_is_not_open_for_investigator_location_if_provided(self):
        survey = Survey.objects.create(
            name="survey name234", description="rajni surve234y")
        ea = EnumerationArea.objects.create(name="EA2")
        country = LocationType.objects.create(name="Country", slug="country")
        region = LocationType.objects.create(name="Region", slug="region")
        district = LocationType.objects.create(
            name="District", slug='district')
        uganda = Location.objects.create(name="Uganda", type=country)
        kampala = Location.objects.create(
            name="Kampala", tree_parent=uganda, type=district)
        ea.locations.add(kampala)
        self.investigator = Interviewer.objects.create(name="Investigator",
                                                       ea=ea,
                                                       gender='1', level_of_education='Primary',
                                                       language='Eglish', weights=0)
        survey = Survey.objects.create(
            name="survey name333", description="rajni survey33333")
        batch = Batch.objects.create(order=1, survey=survey)
        survey_allocation = SurveyAllocation.objects.create(interviewer=self.investigator, survey=survey, allocation_ea=ea, stage=2,
                                                            status=0)
        self.assertFalse(survey.is_open())

    def test_survey_knows_it_is_closed(self):
        survey = Survey.objects.create(
            name="survey name closed", description="closed")
        ea = EnumerationArea.objects.create(name="EA23")
        country = LocationType.objects.create(name="Country", slug="country")
        region = LocationType.objects.create(name="Region", slug="region")
        district = LocationType.objects.create(
            name="District", slug='district')
        uganda = Location.objects.create(name="Uganda", type=country)
        kampala = Location.objects.create(
            name="Kampala", tree_parent=uganda, type=district)
        ea.locations.add(kampala)
        self.investigator = Interviewer.objects.create(name="Investigator_closed",
                                                       ea=ea,
                                                       gender='1', level_of_education='Primary',
                                                       language='Eglish', weights=0)
        survey = Survey.objects.create(
            name="survey name up for close", description="rajni survey close")
        batch = Batch.objects.create(order=1, survey=survey)
        survey_allocation = SurveyAllocation.objects.create(interviewer=self.investigator, survey=survey, allocation_ea=ea, stage=2,
                                                            status=0)
        self.assertFalse(survey.is_open())

    # def test_saves_survey_with_sample_size_from_form_if_has_sampling_is_true(self):
    #     # form_data = {
    #     #     'name': 'survey rajnikanth',
    #     #     'description': 'survey description rajnikanth',
    #     #     'has_sampling': True,
    #     #     'sample_size': 10,
    #     #     'type': True
    #     # }
    #     self.listing_form = mommy.make(ListingTemplate)
    #     question1 = mommy.make(Question, qset=self.listing_form, answer_type=NumericalAnswer.choice_name())
    #     question2 = mommy.make(Question, qset=self.listing_form, answer_type=TextAnswer.choice_name())
    #     question3 = mommy.make(Question, qset=self.listing_form, answer_type=VideoAnswer.choice_name())
    #     self.client.login(username='demo15', password='demo15')
    #     form_data = {'name': 'survey demo15', 'description': 'survey description demo15',
    #                       'has_sampling': True, 'sample_size': 10,
    #                       'random_sample_label': 'q1 {{%s}} q2: {{%s}}' % (question1.identifier, question2.identifier)}
    #     survey_form = SurveyForm(data=form_data)
    #     Survey.save_sample_size(survey_form)
    #     saved_survey = Survey.objects.filter(
    #         name=form_data['name'], has_sampling=form_data['has_sampling'])
    #     self.failUnless(saved_survey)
    #     self.assertEqual(form_data['sample_size'], saved_survey[0].sample_size)

    # def test_saves_survey_with_sample_size_zero_if_has_sampling_is_false(self):
    #     # form_data = {
    #     #     'name': 'survey rajnisuma',
    #     #     'description': 'survey description rajnisuma',
    #     #     'has_sampling': True,
    #     #     'sample_size': 10,
    #     #     'email_group' : "sudheer.s@dhanushinfotech.net",
    #     #     'random_sample_label' : 
    #     #     'type': True
    #     # }
    #     self.listing_form = mommy.make(ListingTemplate)
    #     question1 = mommy.make(Question, qset=self.listing_form, answer_type=NumericalAnswer.choice_name())
    #     question2 = mommy.make(Question, qset=self.listing_form, answer_type=TextAnswer.choice_name())
    #     question3 = mommy.make(Question, qset=self.listing_form, answer_type=VideoAnswer.choice_name())
    #     self.client.login(username='demo13', password='demo13')
    #     form_data = {'name': 'survey demo13', 'description': 'survey description demo13',
    #                       'has_sampling': True, 'sample_size': 10,
    #                       'random_sample_label': 'q1 {{%s}} q2: {{%s}}' % (question1.identifier, question2.identifier)}

    #     survey_form = SurveyForm(data=form_data)
    #     Survey.save_sample_size(survey_form)
    #     saved_survey = Survey.objects.filter(
    #         name=form_data['name'], has_sampling=form_data['has_sampling'])
    #     self.failUnless(saved_survey)
    #     self.assertEqual(0, saved_survey[0].sample_size)

    def test_unicode_text(self):
        survey = Survey.objects.create(
            name="survey name", description="rajni survey")
        self.assertEqual(survey.name, str(survey))

    def test_knows_currently_open_survey(self):
        country = LocationType.objects.create(name='Country', slug='country')
        district = LocationType.objects.create(
            name='District', slug='district')
        uganda = Location.objects.create(name="Uganda", type=country)
        kampala = Location.objects.create(
            name="Kampala", type=district, tree_parent=uganda)
        open_survey = Survey.objects.create(
            name="open survey", description="open survey")
        closed_survey = Survey.objects.create(
            name="closed survey", description="closed survey")
        another_closed_survey = Survey.objects.create(
            name="another closed survey", description="another closed survey")
        open_batch = Batch.objects.create(
            order=1, name="Open Batch", survey=open_survey)
        closed_batch = Batch.objects.create(
            order=2, name="Closed Batch", survey=closed_survey)
        another_closed_batch = Batch.objects.create(
            order=3, name="Another Closed Batch", survey=another_closed_survey)
        open_batch.open_for_location(kampala)
        self.assertTrue(open_survey.is_open())
        self.assertFalse(closed_survey.is_open())

    def test_returns_none_if_there_is_no_currently_open_survey(self):
        country = LocationType.objects.create(name='Country', slug='country')
        district = LocationType.objects.create(
            name='District', slug='district')
        uganda = Location.objects.create(name="Uganda", type=country)
        kampala = Location.objects.create(
            name="Kampala", type=district, tree_parent=uganda)
        open_survey = Survey.objects.create(
            name="open survey", description="open survey")
        closed_survey = Survey.objects.create(
            name="closed survey", description="closed survey")
        another_closed_survey = Survey.objects.create(
            name="another closed survey", description="another closed survey")
        open_batch = Batch.objects.create(
            order=1, name="Open Batch", survey=open_survey)
        closed_batch = Batch.objects.create(
            order=2, name="Closed Batch", survey=closed_survey)
        another_closed_batch = Batch.objects.create(
            order=3, name="Another Closed Batch", survey=another_closed_survey)
        self.assertFalse(None, open_batch.open_for_location(kampala)[1])

    def test__survey_knows_is_currently_open_for_location(self):
        country = LocationType.objects.create(name='Country', slug='country')
        district = LocationType.objects.create(
            name='District', slug='district')
        uganda = Location.objects.create(name="Uganda", type=country)
        kampala = Location.objects.create(
            name="Kampala", type=district, tree_parent=uganda)
        masaka = Location.objects.create(
            name="masaka", type=district, tree_parent=uganda)
        wakiso = Location.objects.create(
            name="wakiso", type=district, tree_parent=uganda)
        open_survey = Survey.objects.create(
            name="open survey", description="open survey")
        open_batch = Batch.objects.create(
            order=1, name="Open Batch", survey=open_survey)
        open_batch_2 = Batch.objects.create(
            order=2, name="Open Batch 2", survey=open_survey)
        open_batch.open_for_location(kampala)
        open_batch_2.open_for_location(masaka)
        self.assertTrue(open_survey.is_open_for(kampala))
        self.assertTrue(open_survey.is_open_for(masaka))
        self.assertFalse(open_survey.is_open_for(wakiso))
