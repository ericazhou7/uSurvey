from lettuce import *
from random import randint
from survey.models import GroupCondition, HouseholdMemberGroup
from survey.features.page_objects.household_member_groups import GroupConditionListPage, GroupsListingPage


@step(u'And I have 10 conditions')
def and_i_have_10_conditions(step):
    for _ in xrange(10):
        random_number = str(randint(1, 99999))
        try:
            GroupCondition.objects.create(value=random_number, attribute=str(random_number), condition ="EQUALS")
        except Exception:
            pass

@step(u'And I visit conditions listing page')
def and_i_visit_conditions_listing_page(step):
    world.page = GroupConditionListPage(world.browser)
    world.page.visit()
    
@step(u'And I should see the conditions list')
def and_i_should_see_the_conditions_list(step):
    world.page.validate_fields()
    
@step(u'And I have a condition')
def and_i_have_a_condition(step):
    world.condition = GroupCondition.objects.create(value=5, attribute="male", condition ="EQUALS")
    
@step(u'And I have 100 groups with that condition')
def and_i_have_100_groups_with_that_condition(step):
    for _ in xrange(100):
        random_number = randint(1, 99999)
        try:
            HouseholdMemberGroup.objects.create(order=random_number, name="group %d" % random_number)
        except Exception:
            pass

@step(u'And I visit groups listing page')
def and_i_visit_groups_listing_page(step):
    world.page = GroupsListingPage(world.browser)
    world.page.visit()
    
@step(u'Then I should see the groups list paginated')
def then_i_should_see_the_groups_list_paginated(step):
    world.page.validate_fields()
    world.page.validate_pagination()