from datetime import datetime
from django import forms
from django.forms import ModelForm, DateInput
from survey.models.households import HouseholdHead
from survey.interviewer_configs import OCCUPATION, MONTHS
from widgets import InlineRadioSelect
from django.conf import settings


class HouseholdHeadForm(ModelForm):

    class Meta:
        model = HouseholdHead
        fields = ['surname', 'first_name',  'date_of_birth', 'gender',
                  'level_of_education', 'resident_since', 'occupation']
        widgets = {
            'surname': forms.TextInput(attrs={'placeholder': 'Family Name'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'Other Names'}),
            'male': InlineRadioSelect(choices=((True, 'Male'), (False, 'Female'))),
            'occupation': forms.Select(choices= OCCUPATION),
        }
    date_of_birth = forms.DateField(label="Date of birth", required=True,
                                    input_formats=[settings.DATE_FORMAT,],
                                    widget=forms.DateInput(attrs={'placeholder': 'Date Of Birth',
                                                                  'class': 'datepicker'},
                                                           format=settings.DATE_FORMAT),)
    resident_since = forms.DateField(required=True, input_formats=[settings.DATE_FORMAT,],
                                     widget= forms.DateInput(attrs={'placeholder': 'Date Of Birth',
                                                                    'class': 'datepicker'},
                                                             format=settings.DATE_FORMAT),
                                     help_text='Date the person started living there')

