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
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

import pickle


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Classifier'
        db.create_table('packaging_classifier', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('classifier', self.gf('djorm_pgarray.fields.ArrayField')(unique=False, null=False, dbtype='text', blank=True, default=None)),
        ))
        db.send_create_signal('packaging', ['Classifier'])

        db.execute("""
            CREATE UNIQUE INDEX packaging_classifier_unq
            ON packaging_classifier
            (classifier)
        """)

        # Adding model 'Project'
        db.create_table('packaging_project', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('warehouse.utils.db_fields.CaseInsensitiveTextField')(unique=True)),
        ))
        db.send_create_signal('packaging', ['Project'])

        # Adding valid name constraint on 'Project'
        db.execute("""
            ALTER TABLE packaging_project
            ADD CONSTRAINT packaging_project_valid_name
            CHECK (
                name ~* '^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$'
            )
        """)

        # Adding uniqueness constraint on 'Project.name' that considers the
        #   equivalent characters equivalent.
        db.execute("""
            CREATE UNIQUE INDEX packaging_project_name_unique_idx
            ON packaging_project
            (
                regexp_replace(
                    regexp_replace(
                        regexp_replace(name, '_', '-', 'ig'),
                        '[1L]', 'I', 'ig'
                    ),
                    '0', 'O', 'ig'
                )
            )
        """)

        # Adding model 'Release'
        db.create_table('packaging_release', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['packaging.Project'])),
            ('version', self.gf('django.db.models.fields.TextField')()),
            ('metadata_version', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('summary', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('description_format', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('source_label', self.gf('warehouse.utils.db_fields.CaseInsensitiveTextField')(blank=True)),
            ('source_url', self.gf('warehouse.utils.db_fields.URLTextField')(blank=True, max_length=200)),
            ('license', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('license_url', self.gf('warehouse.utils.db_fields.URLTextField')(blank=True, max_length=200)),
            ('keywords', self.gf('djorm_pgarray.fields.ArrayField')(null=True, dbtype='text', blank=True, default=None)),
        ))
        db.send_create_signal('packaging', ['Release'])

        # Adding unique constraint on 'Release', fields ['project', 'version']
        db.create_unique('packaging_release', ['project_id', 'version'])

        # Adding unique constraint on 'Release', fields ['project', 'source_label'] conditionally
        db.execute("""
            CREATE UNIQUE INDEX packaging_release_project_source_label_unq
            ON packaging_release (project_id, source_label)
            WHERE source_label != '' AND source_label IS NOT NULL
        """)

        # Adding unique constraint on 'Release', fields ['project', 'source_url'] conditionally
        db.execute("""
            CREATE UNIQUE INDEX packaging_release_project_source_url_unq
            ON packaging_release (project_id, source_url)
            WHERE source_url != '' AND source_url IS NOT NULL
        """)

        # Adding valid source_label constraint for 'Release'
        db.execute("""
            ALTER TABLE packaging_release
            ADD CONSTRAINT packaging_release_valid_source_label
            CHECK (
                source_label ~* '^[A-Z0-9.+-]*$'
            )
        """)

        # Adding valid metadata_version constraint for 'Release'
        db.execute("""
            ALTER TABLE packaging_release
            ADD CONSTRAINT packaging_release_valid_metadata_version
            CHECK (
                metadata_version IN ('1.0', '1.1', '1.2', '2.0')
            )
        """)

        # Adding M2M table for field classifiers on 'Release'
        m2m_table_name = db.shorten_name('packaging_release_classifiers')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('release', models.ForeignKey(orm['packaging.release'], null=False)),
            ('classifier', models.ForeignKey(orm['packaging.classifier'], null=False))
        ))
        db.create_unique(m2m_table_name, ['release_id', 'classifier_id'])

        # Adding model 'ProjectURL'
        db.create_table('packaging_projecturl', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='project_urls', to=orm['packaging.Release'])),
            ('label', self.gf('warehouse.utils.db_fields.CaseInsensitiveTextField')()),
            ('url', self.gf('warehouse.utils.db_fields.URLTextField')(max_length=200)),
        ))
        db.send_create_signal('packaging', ['ProjectURL'])

        # Adding unique constraint on 'ProjectURL', fields ['release', 'label']
        db.create_unique('packaging_projecturl', ['release_id', 'label'])

        # Adding enum 'ContactType'
        db.execute("""
            CREATE TYPE contact_role AS ENUM (
                'author',
                'maintainer',
                'contributor'
            )
        """)

        # Adding model 'Contact'
        db.create_table('packaging_contact', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='contacts', to=orm['packaging.Release'])),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('email', self.gf('django.db.models.fields.EmailField')(blank=True, max_length=254)),
            ('url', self.gf('warehouse.utils.db_fields.URLTextField')(blank=True, max_length=200)),
            ('role', self.gf('django_pgenum.enum.EnumField')(enum=pickle.loads(b'\x80\x03cwarehouse.packaging.models\nContactRole\nq\x00.'))),
        ))
        db.send_create_signal('packaging', ['Contact'])

        # Adding model 'Contributor'
        db.create_table('packaging_contributor', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='contributors', to=orm['packaging.Release'])),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('email', self.gf('django.db.models.fields.EmailField')(blank=True, max_length=254)),
            ('url', self.gf('warehouse.utils.db_fields.URLTextField')(blank=True, max_length=200)),
            ('role', self.gf('django_pgenum.enum.EnumField')(enum=pickle.loads(b'\x80\x03cwarehouse.packaging.models\nContactRole\nq\x00.'))),
        ))
        db.send_create_signal('packaging', ['Contributor'])


    def backwards(self, orm):
        # Removing unique constraint on 'ProjectURL', fields ['release', 'label']
        db.delete_unique('packaging_projecturl', ['release_id', 'label'])

        # Removing unique constraint on 'Release', fields ['project', 'version']
        db.delete_unique('packaging_release', ['project_id', 'version'])

        # Deleting model 'Classifier'
        db.delete_table('packaging_classifier')

        # Deleting model 'Project'
        db.delete_table('packaging_project')

        # Deleting model 'Release'
        db.delete_table('packaging_release')

        # Removing M2M table for field classifiers on 'Release'
        db.delete_table(db.shorten_name('packaging_release_classifiers'))

        # Deleting model 'ProjectURL'
        db.delete_table('packaging_projecturl')

        # Deleting model 'Contact'
        db.delete_table('packaging_contact')

        # Deleting model 'Contributor'
        db.delete_table('packaging_contributor')

        # Deleting the enum 'ContactRole'
        db.execute("DROP TYPE contact_role")

    models = {
        'packaging.classifier': {
            'Meta': {'object_name': 'Classifier'},
            'classifier': ('djorm_pgarray.fields.ArrayField', [], {'unique': 'False', 'null': 'False', 'dbtype': "'text'", 'blank': 'True', 'default': 'None'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'packaging.contact': {
            'Meta': {'object_name': 'Contact'},
            'email': ('django.db.models.fields.EmailField', [], {'blank': 'True', 'max_length': '254'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'contacts'", 'to': "orm['packaging.Release']"}),
            'role': ('django_pgenum.enum.EnumField', [], {'enum': "pickle.loads(b'\\x80\\x03cwarehouse.packaging.models\\nContactRole\\nq\\x00.')"}),
            'url': ('warehouse.utils.db_fields.URLTextField', [], {'blank': 'True', 'max_length': '200'})
        },
        'packaging.contributor': {
            'Meta': {'object_name': 'Contributor'},
            'email': ('django.db.models.fields.EmailField', [], {'blank': 'True', 'max_length': '254'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'contributors'", 'to': "orm['packaging.Release']"}),
            'role': ('django_pgenum.enum.EnumField', [], {'enum': "pickle.loads(b'\\x80\\x03cwarehouse.packaging.models\\nContactRole\\nq\\x00.')"}),
            'url': ('warehouse.utils.db_fields.URLTextField', [], {'blank': 'True', 'max_length': '200'})
        },
        'packaging.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('warehouse.utils.db_fields.CaseInsensitiveTextField', [], {'unique': 'True'})
        },
        'packaging.projecturl': {
            'Meta': {'object_name': 'ProjectURL', 'unique_together': "[('release', 'label')]"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('warehouse.utils.db_fields.CaseInsensitiveTextField', [], {}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project_urls'", 'to': "orm['packaging.Release']"}),
            'url': ('warehouse.utils.db_fields.URLTextField', [], {'max_length': '200'})
        },
        'packaging.release': {
            'Meta': {'object_name': 'Release', 'unique_together': "[('project', 'version')]"},
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['packaging.Classifier']", 'symmetrical': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'description_format': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('djorm_pgarray.fields.ArrayField', [], {'null': 'True', 'dbtype': "'text'", 'blank': 'True', 'default': 'None'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license_url': ('warehouse.utils.db_fields.URLTextField', [], {'blank': 'True', 'max_length': '200'}),
            'metadata_version': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packaging.Project']"}),
            'source_label': ('warehouse.utils.db_fields.CaseInsensitiveTextField', [], {'blank': 'True'}),
            'source_url': ('warehouse.utils.db_fields.URLTextField', [], {'blank': 'True', 'max_length': '200'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['packaging']
