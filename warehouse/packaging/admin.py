# Copyright 2013 Donald Stufft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django import forms

from django.contrib import admin

from django_pgenum import enum
from djorm_pgarray.fields import ArrayFormField

from warehouse.packaging.models import Classifier, Project, Release, ProjectURL
from warehouse.packaging.models import ContactRole, Contact, Contributor
from warehouse.utils.db_fields import CaseInsensitiveTextField


class ClassifierAdminForm(forms.ModelForm):

    classifier = ArrayFormField(
                    delim=" :: ",
                    widget=forms.TextInput(attrs={"size": 100}),
                )

    class Meta:
        model = Classifier
        fields = ["classifier"]


class ClassifierAdmin(admin.ModelAdmin):
    form = ClassifierAdminForm
    ordering = ["classifier"]
    search_fields = ["classifier"]


class ProjectAdmin(admin.ModelAdmin):
    formfield_overrides = {
        CaseInsensitiveTextField: {
            "widget": forms.TextInput(attrs={"size": 100}),
        },
    }
    search_fields = ["name"]


class ProjectURLInlineForm(forms.ModelForm):

    label = forms.CharField()

    class Meta:
        model = ProjectURL
        fields = ["label", "url"]


class ProjectURLInline(admin.TabularInline):
    model = ProjectURL
    extra = 0
    form = ProjectURLInlineForm


class ContactInlineForm(forms.ModelForm):

    name = forms.CharField(widget=forms.TextInput(attrs={"size": 50}))
    role = enum.EnumFormField(ContactRole)

    class Meta:
        model = Contact
        fields = ["name", "email", "url", "role"]


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0
    form = ContactInlineForm


class ContributorInlineForm(forms.ModelForm):

    name = forms.CharField(widget=forms.TextInput(attrs={"size": 50}))
    role = enum.EnumFormField(ContactRole)

    class Meta:
        model = Contributor
        fields = ["name", "email", "url", "role"]


class ContributorInline(admin.TabularInline):
    model = Contributor
    extra = 0
    form = ContributorInlineForm


class ReleaseAdminForm(forms.ModelForm):

    version = forms.CharField()
    summary = forms.CharField(
                    required=False,
                    widget=forms.TextInput(attrs={"size": "90"}),
                )
    description_format = forms.CharField(required=False)
    source_label = forms.CharField(required=False)

    class Meta:
        model = Release
        fields = [
            "project", "version", "metadata_version", "summary", "description",
            "description_format", "source_label", "source_url", "license",
            "license_url", "keywords", "classifiers",
        ]


class ReleaseAdmin(admin.ModelAdmin):
    form = ReleaseAdminForm
    list_display = ["project", "version", "summary"]
    list_filter = ["metadata_version"]
    search_fields = ["project__name", "version"]
    raw_id_fields = ["project"]
    readonly_fields = ["keywords"]

    inlines = [
        ProjectURLInline,
        ContactInline,
        ContributorInline,
    ]


admin.site.register(Classifier, ClassifierAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Release, ReleaseAdmin)
