# Tests for the server-side Variant support: the Book.variant, the
# EngineConfig.variants and EngineConfig.protocol fields, the import commands
# that fill them, and the verification done when a Workload is created.

import json
import os
import tempfile

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from OpenBench.models import Book, EngineConfig
from OpenBench.variants import DEFAULT_ENGINE_VARIANTS, DEFAULT_VARIANT

# Imported first so that OpenBench.utils and OpenBench.views resolve in their
# usual order; importing verify_workload directly first hits their cycle
import OpenBench.views # noqa: F401

from OpenBench.workloads.verify_workload import (
    resolve_book_variant, verify_datagen_creation, verify_test_creation,
    verify_tune_creation,
)

SHA = 'a' * 64
SOURCE = 'https://raw.githubusercontent.com/OpenBench/books/master/book.epd.zip'

ENGINE = {
    'private' : False,
    'nps'     : 1000,
    'source'  : 'https://github.com/OpenBench/Engine',
    'build'   : { 'path' : '', 'compilers' : ['g++'], 'cpuflags' : [], 'systems' : [] },
}

class FakeRequest(object):
    def __init__(self, post): self.POST = post

def write_json(directory, name, data):
    path = os.path.join(directory, '%s.json' % (name))
    with open(path, 'w') as fout:
        json.dump(data, fout)
    return path

def variant_errors(errors):
    return [error for error in errors if 'book variant' in error or 'protocol' in error]

class ModelTests(TestCase):

    def test_book_defaults_to_standard(self):
        self.assertEqual(Book().variant, DEFAULT_VARIANT)

    def test_engine_defaults_to_chess_variants_and_uci(self):
        engine = EngineConfig()
        self.assertEqual(engine.variants, ' '.join(DEFAULT_ENGINE_VARIANTS))
        self.assertEqual(engine.protocol, 'uci')

    def test_variants_list_parses_space_separated_values(self):
        engine = EngineConfig(variants='standard shatranj')
        self.assertEqual(engine.variants_list(), ['standard', 'shatranj'])

    def test_variants_list_ignores_extra_whitespace(self):
        engine = EngineConfig(variants='  shatranj   standard  ')
        self.assertEqual(engine.variants_list(), ['shatranj', 'standard'])

    def test_variants_list_treats_blank_as_the_default(self):
        for blank in ['', '   ']:
            engine = EngineConfig(variants=blank)
            self.assertEqual(engine.variants_list(), list(DEFAULT_ENGINE_VARIANTS))

class ImportBookTests(TestCase):

    def test_variant_is_read_from_the_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, 'Shatranj', {
                'sha' : SHA, 'source' : SOURCE, 'variant' : 'shatranj' })
            call_command('import_books', path, stdout=StringIO())

        self.assertEqual(Book.objects.get(name='Shatranj').variant, 'shatranj')

    def test_variant_defaults_to_standard(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, 'Plain', { 'sha' : SHA, 'source' : SOURCE })
            call_command('import_books', path, stdout=StringIO())

        self.assertEqual(Book.objects.get(name='Plain').variant, 'standard')

    def test_unknown_variant_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, 'Bad', {
                'sha' : SHA, 'source' : SOURCE, 'variant' : 'chess' })
            with self.assertRaises(CommandError):
                call_command('import_books', path, stdout=StringIO())

        self.assertFalse(Book.objects.filter(name='Bad').exists())

    def test_reimport_updates_in_place_and_leaves_enabled_alone(self):
        with tempfile.TemporaryDirectory() as directory:

            path = write_json(directory, 'Repeat', {
                'sha' : SHA, 'source' : SOURCE, 'variant' : 'standard' })
            call_command('import_books', path, stdout=StringIO())

            Book.objects.filter(name='Repeat').update(enabled=False)

            path = write_json(directory, 'Repeat', {
                'sha' : SHA, 'source' : SOURCE, 'variant' : 'shatranj' })
            call_command('import_books', path, stdout=StringIO())

        self.assertEqual(Book.objects.filter(name='Repeat').count(), 1)
        book = Book.objects.get(name='Repeat')
        self.assertEqual(book.variant, 'shatranj')
        self.assertFalse(book.enabled)

class ImportEngineTests(TestCase):

    def test_variants_and_protocol_are_read_from_the_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, 'ShatranjBot', {
                **ENGINE, 'variants' : ['shatranj'], 'protocol' : 'xboard' })
            call_command('import_engines', path, stdout=StringIO())

        engine = EngineConfig.objects.get(name='ShatranjBot')
        self.assertEqual(engine.variants, 'shatranj')
        self.assertEqual(engine.protocol, 'xboard')

    def test_defaults_are_the_chess_variants_and_uci(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, 'ChessBot', ENGINE)
            call_command('import_engines', path, stdout=StringIO())

        engine = EngineConfig.objects.get(name='ChessBot')
        self.assertEqual(engine.variants, 'standard fischerandom')
        self.assertEqual(engine.protocol, 'uci')

    def test_unknown_variant_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, 'Bad', { **ENGINE, 'variants' : ['chess'] })
            with self.assertRaises(CommandError):
                call_command('import_engines', path, stdout=StringIO())

        self.assertFalse(EngineConfig.objects.filter(name='Bad').exists())

    def test_variants_must_be_an_array(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, 'Bad', { **ENGINE, 'variants' : 'shatranj' })
            with self.assertRaises(CommandError):
                call_command('import_engines', path, stdout=StringIO())

        self.assertFalse(EngineConfig.objects.filter(name='Bad').exists())

    def test_unknown_protocol_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, 'Bad', { **ENGINE, 'protocol' : 'chess' })
            with self.assertRaises(CommandError):
                call_command('import_engines', path, stdout=StringIO())

        self.assertFalse(EngineConfig.objects.filter(name='Bad').exists())

    def test_reimport_updates_in_place_and_leaves_enabled_alone(self):
        with tempfile.TemporaryDirectory() as directory:

            path = write_json(directory, 'Repeat', {
                **ENGINE, 'variants' : ['shatranj'] })
            call_command('import_engines', path, stdout=StringIO())

            EngineConfig.objects.filter(name='Repeat').update(enabled=False)

            path = write_json(directory, 'Repeat', {
                **ENGINE, 'variants' : ['standard'] })
            call_command('import_engines', path, stdout=StringIO())

        self.assertEqual(EngineConfig.objects.filter(name='Repeat').count(), 1)
        engine = EngineConfig.objects.get(name='Repeat')
        self.assertEqual(engine.variants, 'standard')
        self.assertFalse(engine.enabled)

class VerificationTests(TestCase):

    def setUp(self):

        Book.objects.create(name='Standard.epd', source=SOURCE, sha=SHA, variant='standard')
        Book.objects.create(name='FRC.epd', source=SOURCE, sha=SHA, variant='fischerandom')
        Book.objects.create(name='shatranj_dfrs.epd', source=SOURCE, sha=SHA, variant='shatranj')

        EngineConfig.objects.create(name='ChessBot')
        EngineConfig.objects.create(name='ShatranjBot', variants='shatranj')
        EngineConfig.objects.create(name='XboardShatranj', variants='shatranj', protocol='xboard')
        EngineConfig.objects.create(name='XboardChess', protocol='xboard')

    def test_resolving_the_book_variant(self):
        self.assertEqual(resolve_book_variant('NONE'), 'standard')
        self.assertEqual(resolve_book_variant(''), 'standard')
        self.assertEqual(resolve_book_variant('Missing.epd'), 'standard')
        self.assertEqual(resolve_book_variant('FRC.epd'), 'fischerandom')
        self.assertEqual(resolve_book_variant('shatranj_dfrs.epd'), 'shatranj')

    def test_standard_and_frc_books_pass_with_default_engines(self):
        for book in ['Standard.epd', 'FRC.epd']:
            errors = []
            verify_test_creation(errors, FakeRequest({
                'book_name' : book, 'dev_engine' : 'ChessBot', 'base_engine' : 'ChessBot',
                'syzygy_wdl' : 'OPTIONAL', 'syzygy_adj' : 'OPTIONAL',
            }))
            self.assertEqual(variant_errors(errors), [], 'Unexpected errors for %s' % (book))

    def test_shatranj_book_rejects_a_default_chess_engine(self):
        errors = []
        verify_test_creation(errors, FakeRequest({
            'book_name' : 'shatranj_dfrs.epd',
            'dev_engine' : 'ChessBot', 'base_engine' : 'ChessBot',
            'syzygy_wdl' : 'DISABLED', 'syzygy_adj' : 'DISABLED',
        }))

        self.assertIn('Dev Variant: ChessBot does not accept the shatranj book variant', errors)
        self.assertIn('Base Variant: ChessBot does not accept the shatranj book variant', errors)

    def test_shatranj_book_rejects_an_xboard_engine(self):
        errors = []
        verify_test_creation(errors, FakeRequest({
            'book_name' : 'shatranj_dfrs.epd',
            'dev_engine' : 'ShatranjBot', 'base_engine' : 'XboardShatranj',
            'syzygy_wdl' : 'DISABLED', 'syzygy_adj' : 'DISABLED',
        }))

        self.assertIn(
            'Base Protocol: XboardShatranj uses the xboard protocol, '
            'but the match runner only supports UCI',
            errors)

        # The UCI engine on the same Book is fine
        self.assertFalse(any('ShatranjBot' in error for error in variant_errors(errors)))

    def test_xboard_engines_are_rejected_on_any_book(self):

        # fastchess speaks UCI only, so an xboard Engine can never be launched,
        # whatever the variant of the Book happens to be

        for book in ['Standard.epd', 'FRC.epd']:

            errors = []
            verify_test_creation(errors, FakeRequest({
                'book_name' : book,
                'dev_engine' : 'XboardChess', 'base_engine' : 'XboardChess',
                'syzygy_wdl' : 'OPTIONAL', 'syzygy_adj' : 'OPTIONAL',
            }))

            for branch in ['Dev', 'Base']:
                self.assertIn(
                    '%s Protocol: XboardChess uses the xboard protocol, '
                    'but the match runner only supports UCI' % (branch),
                    errors)

    def test_tune_rejects_an_xboard_engine(self):

        errors = []
        verify_tune_creation(errors, FakeRequest({
            'book_name' : 'Standard.epd', 'dev_engine' : 'XboardChess',
            'syzygy_wdl' : 'OPTIONAL', 'syzygy_adj' : 'OPTIONAL',
            'spsa_inputs' : 'Test, int, 1, 0, 10, 0, 1',
        }))

        self.assertIn(
            'Dev Protocol: XboardChess uses the xboard protocol, '
            'but the match runner only supports UCI',
            errors)
        self.assertFalse(any('Base' in error for error in errors))

    def test_shatranj_requires_syzygy_to_be_disabled(self):
        errors = []
        verify_test_creation(errors, FakeRequest({
            'book_name' : 'shatranj_dfrs.epd',
            'dev_engine' : 'ShatranjBot', 'base_engine' : 'ShatranjBot',
            'syzygy_wdl' : 'OPTIONAL', 'syzygy_adj' : 'OPTIONAL',
        }))

        self.assertIn('Syzygy WDL: shatranj books require Syzygy to be DISABLED', errors)
        self.assertIn('Syzygy Adjudication: shatranj books require Syzygy to be DISABLED', errors)

    def test_shatranj_with_syzygy_disabled_passes(self):
        errors = []
        verify_test_creation(errors, FakeRequest({
            'book_name' : 'shatranj_dfrs.epd',
            'dev_engine' : 'ShatranjBot', 'base_engine' : 'ShatranjBot',
            'syzygy_wdl' : 'DISABLED', 'syzygy_adj' : 'DISABLED',
        }))

        self.assertEqual(variant_errors(errors), [])

    def test_tune_only_checks_the_dev_engine(self):
        errors = []
        verify_tune_creation(errors, FakeRequest({
            'book_name' : 'shatranj_dfrs.epd', 'dev_engine' : 'ChessBot',
            'syzygy_wdl' : 'DISABLED', 'syzygy_adj' : 'DISABLED',
            'spsa_inputs' : 'Test, int, 1, 0, 10, 0, 1',
        }))

        self.assertEqual(len(variant_errors(errors)), 1)
        self.assertIn('Dev Variant: ChessBot does not accept the shatranj book variant', errors)
        self.assertFalse(any('Base' in error for error in errors))

    def test_a_none_book_is_treated_as_standard(self):
        errors = []
        verify_datagen_creation(errors, FakeRequest({
            'book_name' : 'NONE', 'dev_engine' : 'ChessBot', 'base_engine' : 'ChessBot',
            'syzygy_wdl' : 'OPTIONAL', 'syzygy_adj' : 'OPTIONAL',
        }))

        self.assertEqual(variant_errors(errors), [])

    def test_datagen_checks_both_engines(self):
        errors = []
        verify_datagen_creation(errors, FakeRequest({
            'book_name' : 'shatranj_dfrs.epd',
            'dev_engine' : 'ChessBot', 'base_engine' : 'ChessBot',
            'syzygy_wdl' : 'DISABLED', 'syzygy_adj' : 'DISABLED',
        }))

        self.assertIn('Dev Variant: ChessBot does not accept the shatranj book variant', errors)
        self.assertIn('Base Variant: ChessBot does not accept the shatranj book variant', errors)
