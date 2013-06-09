#!/usr/bin/env python
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
from configurations import importer
importer.install()

from django.db import connection
from django.utils.timezone import utc

from warehouse.accounts.models import User, Email
from warehouse.packaging.models import Classifier, Project, Release
from warehouse.packaging.models import ProjectURL, Contact, ContactRole


def empty(value):
    if not value or value == "UNKNOWN":
        return True
    return False


cursor = connection.cursor()

# Copy over PyPI users into Django users
cursor.execute("SELECT name, password, last_login FROM users")
users = []
usernames = []
usernames_last_login = []
for name, password, last_login in cursor.fetchall():
    user = User(username=name)

    # Bring over the password from passlib format into Django format
    if password.startswith("$2a$"):
        user.password = "bcrypt$" + password
    else:
        user.password = password

    # Stash what users need their last_login set
    if last_login is None:
        usernames_last_login.append(name)
    else:
        user.last_login = last_login.replace(tzinfo=utc)

    # Stash all of our usernames so we can set their date_joined to infinity
    usernames.append(name)

    # Add the user to our list of users to create
    users.append(user)

# Create the users
User.objects.bulk_create(users)

# Set users who didn't have a last login to infinity date time
cursor.execute("""
    UPDATE accounts_user SET last_login = '-infinity' WHERE username IN %s
""", (tuple(usernames_last_login),))

# Set all of our date_joined to infinity since we don't have that data
cursor.execute("""
    UPDATE accounts_user SET date_joined = '-infinity' WHERE username IN %s
""", (tuple(usernames),))


# For each PyPI user with an email address, create a Warehouse Email
cursor.execute("""
    SELECT DISTINCT ON (users.email) accounts_user.id, users.email
    FROM users, accounts_user
    WHERE users.name = accounts_user.username AND users.email IS NOT NULL
""")
emails = [Email(user_id=user_id, email=email, primary=True, verified=True)
                for user_id, email in cursor.fetchall()]
Email.objects.bulk_create(emails)


# Get our Super Admins created by using the 'Admin' role
cursor.execute("SELECT user_name FROM roles where role_name = 'Admin'")
admins = [x[0] for x in cursor.fetchall()]
User.objects.filter(
    username__in=admins).update(is_staff=True, is_superuser=True)


# Import the classifers
cursor.execute(
    "SELECT regexp_split_to_array(classifier, ' :: ') FROM trove_classifiers")
classifiers = [Classifier(classifier=c[0]) for c in cursor.fetchall()]
Classifier.objects.bulk_create(classifiers)

# Import the existing package names
#   Temporarily restrict the name until PyPI names are all sanitized
cursor.execute("""
    SELECT name FROM PACKAGES
    WHERE name ~* '^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$'
""")
projects = [Project(name=n[0]) for n in cursor.fetchall()]
Project.objects.bulk_create(projects)

# Import existing releases
cursor.execute("""
    SELECT packaging_project.id, version, summary, description, license,
                string_to_array(keywords, ' '), home_page, download_url
    FROM releases, packaging_project
    WHERE releases.name = packaging_project.name
""")
releases = []
for (project_id, version, summary, description, license, keywords,
        home_page, download_url) in cursor.fetchall():
    release = Release(project_id=project_id, version=version)

    # TODO: Figure out how we can detect the metadata_version, or a safe
    #           static metadata_version
    release.metadata_version = "1.1"

    if not empty(summary):
        release.summary = summary

    if not empty(description):
        release.description = description

        # Attempt to render release.description and set txt or rst depending

    if not empty(license):
        release.license = license

    # TODO: Come up with a better way of splitting this than just on space?
    if keywords:
        release.keywords = keywords

    releases.append(release)

# Actually create our releases
Release.objects.bulk_create(releases)

# We will need the id's of our Releases so build them up here
all_releases = {(r.project.name, r.version): r.id
                    for r in Release.objects.all().select_related("project")}

# Create our Project URLs
cursor.execute("SELECT name, version, home_page, download_url FROM releases")
project_urls = []
for name, version, home_page, download_url in cursor.fetchall():
    release = all_releases.get((name, version), None)
    if release is None:
        # Temporary to deal with projects we haven't ported yet
        continue

    if not empty(home_page):
        project_urls += [
            ProjectURL(release_id=release, label="Home", url=home_page),
        ]

    if not empty(download_url):
        project_urls += [
            ProjectURL(release_id=release, label="Download", url=download_url),
        ]

# Actually create our Project URLs
ProjectURL.objects.bulk_create(project_urls)


# Import our authors and maintainers
cursor.execute("""
    SELECT name, version, author, author_email, maintainer, maintainer_email
    FROM releases
""")
contacts = []
for (name, version, author, author_email, maintainer, maintainer_email
                                                    ) in cursor.fetchall():
    release = all_releases.get((name, version), None)
    if release is None:
        # Temporary to deal with projects we haven't ported yet
        continue

    if not empty(author) or not empty(author_email):
        c = Contact(release_id=release, role=ContactRole.author)

        if not empty(author):
            c.name = author

        if not empty(author_email):
            c.email = author_email

        contacts.append(c)

    if not empty(maintainer) or not empty(maintainer_email):
        c = Contact(release_id=release, role=ContactRole.maintainer)

        if not empty(maintainer):
            c.name = maintainer

        if not empty(maintainer_email):
            c.email = maintainer_email

        contacts.append(c)

# Create all of our contacts
Contact.objects.bulk_create(contacts)
