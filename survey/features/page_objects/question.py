from survey.features.page_objects.base import PageObject
from nose.tools import assert_equals


class BatchQuestionsListPage(PageObject):
    def __init__(self, browser, batch):
        self.browser = browser
        self.batch = batch
        self.url = '/batches/%d/questions/' % batch.id

    def validate_fields(self):
        self.is_text_present('%s Question' % self.batch.name.capitalize())
        self.is_text_present('Question')
        self.is_text_present('Type')
        self.is_text_present('Group')
        self.is_text_present('Actions')

    def validate_pagination(self):
        self.browser.click_link_by_text("2")


class ListAllQuestionsPage(PageObject):
    url = "/questions/"

    def validate_fields(self):
        self.validate_fields_present(['Questions List', 'Question', 'Type', 'Group', 'Actions'])

    def validate_back_to_questions_list_page(self):
        assert_equals(False, self.browser.is_text_present("Text"))
        assert_equals(False, self.browser.is_text_present("Order"))
        assert_equals(False, self.browser.is_text_present("Close"))


class AddQuestionPage(PageObject):
    def __init__(self, browser, batch):
        self.browser = browser
        self.batch = batch
        self.url = '/batches/%d/questions/new/' % batch.id


class CreateNewQuestionPage(PageObject):
    url = "/questions/new/"

    def see_one_option_field(self, option):
        self.is_text_present(option)

    def see_option_add_and_remove_buttons(self, length):
        assert len(self.browser.find_by_css(".icon-plus")) == length
        assert len(self.browser.find_by_css(".icon-remove")) == length

    def option_not_present(self, option):
        assert not self.browser.is_text_present(option)

    def see_option_text(self, option_text, field_name):
        elements = self.browser.find_by_name(field_name)
        for element in elements:
            if option_text in element.text:
                return True
        return False


class CreateNewSubQuestionPage(PageObject):
    def __init__(self, browser, question):
        self.browser = browser
        self.question = question
        self.url = "/questions/%d/sub_questions/new/" % question.id