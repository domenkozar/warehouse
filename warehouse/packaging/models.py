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
import re

from django.core import validators
from django.db import models
from django.utils.translation import ugettext_lazy as _


from django_pgenum import enum
from djorm_pgarray.fields import ArrayField

from warehouse.utils.db_fields import URLTextField, CaseInsensitiveTextField


_valid_project_name_regex = re.compile(
    # Ensure that a project name:
    #   - Contains only letters, digits, underscores, hyphens, and periods
    #   - Starts and ends with a letter or digit
    r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$",
    re.IGNORECASE,
)

_valid_source_label_regex = re.compile(
    # Ensure that a build label:
    #   - Contains only letters, digits, hyphens, periods, and pluses
    r"^[A-Z0-9.+-]+$",
    re.IGNORECASE,
)


class Classifier(models.Model):

    classifier = ArrayField(dbtype="text", unique=True)

    class Meta:
        verbose_name = _("Classifier")
        verbose_name_plural = _("Classifiers")


class Project(models.Model):

    # There is a UNIQUE INDEX on Project.name that transform name prior to
    #   doing the uniqueness check:
    #       - ``_`` is transformed to ``-``
    #       - ``1`` and ``L`` is transformed to ``I``
    #       - ``0`` is transformed to ``O``

    # There is a CHECK CONSTRAINT on Project that ensures that Project.name
    #   is a valid name. It checks that:
    #       - name begins and ends with ASCII letter or digit
    #       - name contains only ASCII letters, digits, periods, hyphens, and
    #           underscores

    # TODO: Put uniqueness via transforms into the code

    name = CaseInsensitiveTextField(_("Name"),
                    unique=True,
                    validators=[
                        validators.RegexValidator(
                            _valid_project_name_regex,
                            _("This value may contain only letters, numbers, "
                                "and ./-/_ characters."),
                            "invalid",
                        ),
                    ],
                )

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")


class Release(models.Model):

    # There is a CHECK CONSTRAINT on Release that ensures that
    #   Release.source_label is a valid name. It checks that:
    #       - build_label contains only ASCII letters, digits, periods,
    #           hyphens, and pluses

    # There is a CHECK CONSTRAINT on Release that ensures that
    #   Release.metadata_version is a valid value. The valid values are 1.0,
    #   1.1, 1.2, and 2.0.

    # There is a UNIQUE INDEX on (Release.project, Release.source_label) that
    #   ensures whenever source_label has a value, that it's unique per project

    # There is a UNIQUE INDEX on (Release.project, Release.source_url) that
    #   ensures whenever source_url has a value, that it's unique per project

    # TODO: Ensure valid version in the code when metadata == 2.0

    # Required fields
    project = models.ForeignKey(Project, verbose_name=_("Project"))
    version = models.TextField(_("Version"))
    metadata_version = models.CharField(_("Metadata Version"),
                            choices=[
                                ("1.0", "1.0"), ("1.1", "1.1"),
                                ("1.2", "1.2"), ("2.0", "2.0"),
                            ],
                            max_length=3,
                        )

    # Optional fields
    summary = models.TextField(_("Summary"), blank=True)
    description = models.TextField(_("Description"), blank=True)
    description_format = models.TextField(_("Description Format"), blank=True)
    source_label = CaseInsensitiveTextField(_("Source label"),
                    blank=True,
                    validators=[
                        validators.RegexValidator(
                            _valid_source_label_regex,
                            _("This value may contain only letters, numbers, "
                                "and ./-/+ characters."),
                            "invalid",
                        ),
                    ],
                )
    source_url = URLTextField(_("Source URL"), blank=True)
    license = models.TextField(_("License"), blank=True)
    license_url = URLTextField(_("License URL"), blank=True)
    keywords = ArrayField(dbtype="text")
    classifiers = models.ManyToManyField(Classifier, blank=True)

    class Meta:
        verbose_name = _("Release")
        verbose_name_plural = _("Releases")

        unique_together = [
            # Each project should have at most one of a particular version
            ("project", "version"),
        ]


class ProjectURL(models.Model):

    release = models.ForeignKey(Release,
                        verbose_name=_("Release"),
                        related_name="project_urls",
                    )

    label = CaseInsensitiveTextField(_("Label"))
    url = URLTextField(_("URL"))

    class Meta:
        verbose_name = _("Project URL")
        verbose_name_plural = _("Project URLs")

        unique_together = [
            # Labels are unique per release
            ("release", "label"),
        ]


class ContactRole(enum.Enum):

    author = (..., _("Author"))
    maintainer = (..., _("Maintainer"))
    contributor = (..., _("Contributor"))


class Contact(models.Model):

    release = models.ForeignKey(Release,
                        verbose_name=_("Release"),
                        related_name="contacts",
                    )

    name = models.TextField(_("Name"))
    email = models.EmailField(_("Email"), max_length=254, blank=True)
    url = URLTextField(_("URL"), blank=True)
    role = enum.EnumField(ContactRole,
                    verbose_name=_("Role"),
                    default=ContactRole.contributor,
                )

    class Meta:
        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")


class Contributor(models.Model):

    release = models.ForeignKey(Release,
                        verbose_name=_("Release"),
                        related_name="contributors",
                    )

    name = models.TextField(_("Name"))
    email = models.EmailField(_("Email"), max_length=254, blank=True)
    url = URLTextField(_("URL"), blank=True)
    role = enum.EnumField(ContactRole,
                    verbose_name=_("Role"),
                    default=ContactRole.contributor,
                )

    class Meta:
        verbose_name = _("Contributor")
        verbose_name_plural = _("Contributors")
