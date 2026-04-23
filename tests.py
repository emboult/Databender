"""
Databender – Unit Test Suite
=============================
Καλύπτει: formats.py, history.py, ops.py, state.py
Εκτέλεση: python -m pytest test_databender.py -v
          ή: python test_databender.py
"""

import sys
import os
import unittest
import random
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup – επιτρέπει εκτέλεση είτε από ριζικό φάκελο είτε από φάκελο project
# ---------------------------------------------------------------------------
PROJECT_DIR = os.path.join(os.path.dirname(__file__), "project")
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, os.path.dirname(__file__))

# Τα modules εισάγονται ως μέρος του package «project»
from model.formats import (
    detect_format,
    printable_latin1_str,
    ensure_magic_bytes,
    get_format_extension,
    decode_bytes,
    encode_bytes,
    register_codec,
    MAGIC_BYTES,
    HAS_PILLOW,
)
from model.history import History
from model.state import AppState
import model.ops as ops


# ===========================================================================
# Βοηθητικές συναρτήσεις
# ===========================================================================

def make_state(data: bytes, sel_start: Optional[int] = None, sel_end: Optional[int] = None) -> AppState:
    """Δημιουργεί AppState, φορτώνει δεδομένα και ορίζει προαιρετικά selection."""
    state = AppState()
    state.load(None, data)
    if sel_start is not None and sel_end is not None:
        state.select(sel_start, sel_end)
    return state


# ===========================================================================
# 1.  formats.py
# ===========================================================================

class TestDetectFormat(unittest.TestCase):
    """detect_format – αναγνώριση μορφής από magic bytes"""

    def test_jpeg(self):
        self.assertEqual(detect_format(b'\xff\xd8\xff' + b'\x00' * 10), "JPEG")

    def test_png(self):
        self.assertEqual(detect_format(b'\x89PNG\r\n\x1a\n' + b'\x00' * 10), "PNG")

    def test_bmp(self):
        self.assertEqual(detect_format(b'BM' + b'\x00' * 20), "BMP")

    def test_gif87a(self):
        self.assertEqual(detect_format(b'GIF87a' + b'\x00' * 10), "GIF")

    def test_gif89a(self):
        self.assertEqual(detect_format(b'GIF89a' + b'\x00' * 10), "GIF")

    def test_tiff_little_endian(self):
        self.assertEqual(detect_format(b'II*\x00' + b'\x00' * 10), "TIFF")

    def test_tiff_big_endian(self):
        self.assertEqual(detect_format(b'MM\x00*' + b'\x00' * 10), "TIFF")

    def test_webp(self):
        data = b'RIFF' + b'\x00' * 4 + b'WEBP' + b'\x00' * 10
        self.assertEqual(detect_format(data), "WEBP")

    def test_ppm_p6(self):
        self.assertEqual(detect_format(b'P6\n100 100\n255\n' + b'\x00' * 10), "PPM")

    def test_ppm_p5(self):
        self.assertEqual(detect_format(b'P5 100 100 255\n' + b'\x00' * 10), "PPM")

    def test_unknown_returns_unknown_or_tga(self):
        # Τυχαία bytes που δεν ξεκινούν με γνωστά magic – αναμένεται "Unknown" ή "TGA"
        result = detect_format(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        self.assertIn(result, ("Unknown", "TGA"))

    def test_empty_bytes(self):
        result = detect_format(b'')
        self.assertIn(result, ("Unknown", "TGA"))

    def test_webp_requires_webp_marker(self):
        # RIFF χωρίς WEBP marker δεν είναι WEBP
        data = b'RIFF' + b'\x00' * 4 + b'WAVE' + b'\x00' * 10
        self.assertNotEqual(detect_format(data), "WEBP")


class TestPrintableLatin1Str(unittest.TestCase):
    """printable_latin1_str – μετατροπή bytes σε εκτυπώσιμο Latin-1"""

    def test_empty(self):
        self.assertEqual(printable_latin1_str(b''), "")

    def test_printable_ascii(self):
        self.assertEqual(printable_latin1_str(b'Hello'), "Hello")

    def test_non_printable_replaced(self):
        result = printable_latin1_str(bytes([0x00, 0x01, 0x1F]))
        self.assertEqual(result, "...")

    def test_latin1_high_range_kept(self):
        # Bytes 0xA0–0xFF είναι εκτυπώσιμα Latin-1
        result = printable_latin1_str(bytes([0xA0, 0xFF]))
        self.assertEqual(len(result), 2)
        for ch in result:
            self.assertNotEqual(ch, '.')

    def test_mixed(self):
        data = bytes([0x41, 0x00, 0x42])  # 'A', non-printable, 'B'
        result = printable_latin1_str(data)
        self.assertEqual(result, "A.B")

    def test_full_printable_range(self):
        # Bytes 0x20–0x7E είναι ASCII εκτυπώσιμα – καμία αντικατάσταση δεν αναμένεται.
        # Η τελεία (0x2E) είναι ΚΑΙ εκτυπώσιμος χαρακτήρας ΚΑΙ το placeholder,
        # άρα δεν μπορούμε να ελέγξουμε με assertNotIn('.').
        # Ελέγχουμε αντ' αυτού ότι το μήκος παραμένει ακριβώς σωστό (1:1 mapping).
        data = bytes(range(0x20, 0x7F))
        result = printable_latin1_str(data)
        self.assertEqual(len(result), len(data))


class TestEnsureMagicBytes(unittest.TestCase):
    """ensure_magic_bytes – εξασφάλιση σωστών magic bytes"""

    def test_jpeg_already_has_magic(self):
        data = b'\xff\xd8\xff' + b'\x00' * 10
        result = ensure_magic_bytes(data, "JPEG")
        self.assertEqual(result, data)

    def test_jpeg_missing_magic_prepended(self):
        data = b'\x00' * 10
        result = ensure_magic_bytes(data, "JPEG")
        self.assertTrue(result.startswith(b'\xff\xd8\xff'))

    def test_png_missing_magic_prepended(self):
        data = b'\x00' * 10
        result = ensure_magic_bytes(data, "PNG")
        self.assertTrue(result.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_unknown_format_unchanged(self):
        data = b'\x01\x02\x03'
        result = ensure_magic_bytes(data, "UNKNOWN_FMT")
        self.assertEqual(result, data)

    def test_none_format_unchanged(self):
        data = b'\x01\x02\x03'
        result = ensure_magic_bytes(data, None)
        self.assertEqual(result, data)

    def test_empty_data_unchanged(self):
        result = ensure_magic_bytes(b'', "JPEG")
        self.assertEqual(result, b'')

    def test_bmp_prepended(self):
        data = b'\x00' * 5
        result = ensure_magic_bytes(data, "BMP")
        self.assertTrue(result.startswith(b'BM'))


class TestGetFormatExtension(unittest.TestCase):
    """get_format_extension – αντιστοίχιση format σε extension"""

    def test_jpeg(self):
        self.assertEqual(get_format_extension("JPEG"), ".jpg")

    def test_png(self):
        self.assertEqual(get_format_extension("PNG"), ".png")

    def test_bmp(self):
        self.assertEqual(get_format_extension("BMP"), ".bmp")

    def test_gif(self):
        self.assertEqual(get_format_extension("GIF"), ".gif")

    def test_tiff(self):
        self.assertEqual(get_format_extension("TIFF"), ".tiff")

    def test_webp(self):
        self.assertEqual(get_format_extension("WEBP"), ".webp")

    def test_ppm(self):
        self.assertEqual(get_format_extension("PPM"), ".ppm")

    def test_tga(self):
        self.assertEqual(get_format_extension("TGA"), ".tga")

    def test_unknown_returns_bin(self):
        self.assertEqual(get_format_extension("UNKNOWN"), ".bin")

    def test_empty_string_returns_bin(self):
        self.assertEqual(get_format_extension(""), ".bin")


class TestDecodeEncodeBytes(unittest.TestCase):
    """decode_bytes / encode_bytes – raw mode"""

    def test_decode_raw_returns_bytes(self):
        data = b'\x01\x02\x03'
        result = decode_bytes(data, fmt=None, mode="raw")
        self.assertIsInstance(result, bytes)
        self.assertEqual(result, data)

    def test_encode_raw_returns_bytes(self):
        data = b'\x01\x02\x03'
        result = encode_bytes(data, target_format="", mode="raw")
        self.assertIsInstance(result, bytes)
        self.assertEqual(result, data)

    def test_decode_unsupported_mode_raises(self):
        with self.assertRaises((ValueError, RuntimeError)):
            decode_bytes(b'\x00', fmt=None, mode="unsupported_mode")

    def test_encode_raw_non_bytes_raises(self):
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            encode_bytes("not bytes", target_format="", mode="raw")

    def test_decode_image_without_pillow_raises(self):
        if HAS_PILLOW:
            self.skipTest("Pillow is available – skipping no-Pillow test")
        with self.assertRaises(RuntimeError):
            decode_bytes(b'\x00' * 100, fmt=None, mode="image")

    def test_register_and_use_custom_codec(self):
        def my_decoder(data, mode):
            return data[::-1]

        def my_encoder(obj, fmt):
            return obj[::-1]

        register_codec("TESTFMT", my_decoder, my_encoder)
        data = b'\x01\x02\x03'
        decoded = decode_bytes(data, fmt="TESTFMT")
        self.assertEqual(decoded, b'\x03\x02\x01')
        encoded = encode_bytes(decoded, target_format="TESTFMT")
        self.assertEqual(encoded, data)


# ===========================================================================
# 2.  history.py
# ===========================================================================

class TestHistoryPushUndoRedo(unittest.TestCase):
    """History – push / undo / redo / clear"""

    def setUp(self):
        self.state = make_state(b'\x01\x02\x03\x04\x05')
        self.history = History()

    def test_initial_cannot_undo_or_redo(self):
        self.assertFalse(self.history.can_undo())
        self.assertFalse(self.history.can_redo())

    def test_push_enables_undo(self):
        patch = (0, b'\x01', b'\xFF')
        self.history.push(patch)
        self.assertTrue(self.history.can_undo())

    def test_push_clears_redo(self):
        # Προσθήκη patch, undo, redo για να γεμίσει το redo stack,
        # μετά νέο push – το redo πρέπει να αδειάσει
        state = self.state
        patch1 = (0, bytes(state.current[0:1]), b'\xAA')
        self.history.push(patch1)
        self.history.undo(state)
        self.assertTrue(self.history.can_redo())
        patch2 = (1, bytes(state.current[1:2]), b'\xBB')
        self.history.push(patch2)
        self.assertFalse(self.history.can_redo())

    def test_undo_restores_state(self):
        state = self.state
        original_byte = bytes(state.current[0:1])
        patch = (0, original_byte, b'\xFF')
        self.history.push(patch)
        state.set_bytes(0, b'\xFF', replace_len=1)  # εφαρμογή της αλλαγής

        self.history.undo(state)
        self.assertEqual(state.current[0:1], original_byte)

    def test_redo_re_applies_change(self):
        state = self.state
        original_byte = bytes(state.current[0:1])
        new_byte = b'\xFF'
        patch = (0, original_byte, new_byte)
        self.history.push(patch)
        state.set_bytes(0, new_byte, replace_len=1)

        self.history.undo(state)
        self.history.redo(state)
        self.assertEqual(state.current[0:1], new_byte)

    def test_undo_on_empty_returns_none(self):
        result = self.history.undo(self.state)
        self.assertIsNone(result)

    def test_redo_on_empty_returns_none(self):
        result = self.history.redo(self.state)
        self.assertIsNone(result)

    def test_clear_resets_stacks(self):
        patch = (0, b'\x01', b'\xFF')
        self.history.push(patch)
        self.history.clear()
        self.assertFalse(self.history.can_undo())
        self.assertFalse(self.history.can_redo())

    def test_multiple_undo_steps(self):
        state = self.state
        patches = [
            (0, b'\x01', b'\xAA'),
            (1, b'\x02', b'\xBB'),
            (2, b'\x03', b'\xCC'),
        ]
        for p in patches:
            state.set_bytes(p[0], p[2], replace_len=1)
            self.history.push(p)

        self.history.undo(state)
        self.history.undo(state)
        self.history.undo(state)

        self.assertFalse(self.history.can_undo())
        self.assertTrue(self.history.can_redo())

    def test_undo_redo_symmetry(self):
        state = self.state
        original = bytes(state.current)
        patch = (0, bytes(state.current[:1]), b'\xDE')
        state.set_bytes(0, b'\xDE', replace_len=1)
        self.history.push(patch)

        self.history.undo(state)
        after_undo = bytes(state.current)

        self.history.redo(state)
        after_redo = bytes(state.current)

        self.assertEqual(after_undo[:1], original[:1])
        self.assertEqual(after_redo[0], 0xDE)


class TestHistoryGetEditHighlights(unittest.TestCase):
    """History.get_edit_highlights – έλεγχος εύρους αλλαγών"""

    def setUp(self):
        self.state = make_state(b'\x00' * 100)
        self.history = History()

    def test_empty_history_returns_none_and_empty(self):
        latest, older = self.history.get_edit_highlights()
        self.assertIsNone(latest)
        self.assertEqual(older, [])

    def test_single_patch_returns_correct_range(self):
        # Patch στη θέση 10, αντικαθιστά 5 bytes
        before = bytes(self.state.current[10:15])
        after = b'\xFF' * 5
        self.history.push((10, before, after))

        latest, older = self.history.get_edit_highlights()
        self.assertIsNotNone(latest)
        start, end = latest
        self.assertEqual(start, 10)
        self.assertEqual(end, 14)  # 10 + 5 - 1

    def test_two_patches_latest_and_older(self):
        self.history.push((0, b'\x00', b'\xAA'))
        self.history.push((5, b'\x00', b'\xBB'))

        latest, older = self.history.get_edit_highlights()
        self.assertIsNotNone(latest)
        self.assertEqual(len(older), 1)

    def test_clear_edit_highlights_hides_old(self):
        self.history.push((0, b'\x00', b'\xAA'))
        self.history.clear_edit_highlights()
        # Μετά το clear, τα προηγούμενα patches δεν εμφανίζονται
        latest, older = self.history.get_edit_highlights()
        self.assertIsNone(latest)
        self.assertEqual(older, [])

    def test_insertion_shifts_later_highlights(self):
        # Patch 1: αντικατάσταση 1 byte με 3 bytes (εισαγωγή 2 bytes)
        self.history.push((0, b'\x00', b'\xAA\xBB\xCC'))
        # Patch 2: αλλαγή στη θέση 5 (που θα "σπρωχτεί" κατά +2)
        self.history.push((5, b'\x00', b'\xFF'))

        latest, older = self.history.get_edit_highlights()
        # Το latest patch (θέση 5) δεν επηρεάζεται – είναι το τελευταίο
        self.assertIsNotNone(latest)
        start_latest, _ = latest
        self.assertEqual(start_latest, 5)

        # Το πρώτο patch (θέση 0) "σπρώχνεται" από το δεύτερο (θέση 5 > 0 + 3-1=2 δεν σπρώχνει το πρώτο)
        if older:
            start_older, end_older = older[0]
            self.assertGreaterEqual(start_older, 0)

    def test_deletion_shrinks_range(self):
        # Patch 1: αντικατάσταση 5 bytes με 1 byte (διαγραφή 4 bytes)
        self.history.push((2, b'\x00' * 5, b'\xAA'))
        latest, older = self.history.get_edit_highlights()
        self.assertIsNotNone(latest)
        start, end = latest
        self.assertEqual(start, 2)
        self.assertEqual(end, 2)  # 2 + 1 - 1


# ===========================================================================
# 3.  ops.py
# ===========================================================================

class TestGlitchRandomize(unittest.TestCase):
    """ops.glitch_randomize"""

    def test_randomize_changes_bytes(self):
        state = make_state(b'\x00' * 20, 0, 9)
        original = bytes(state.current)
        rng = random.Random(42)
        ops.glitch_randomize(state, rng=rng)
        self.assertNotEqual(bytes(state.current), original)

    def test_randomize_only_in_selection(self):
        data = b'\x00' * 20
        state = make_state(data, 5, 9)
        rng = random.Random(42)
        ops.glitch_randomize(state, rng=rng)
        # Bytes εκτός selection πρέπει να παραμένουν αμετάβλητα
        self.assertEqual(bytes(state.current[:5]), data[:5])
        self.assertEqual(bytes(state.current[10:]), data[10:])

    def test_randomize_pushes_to_history(self):
        state = make_state(b'\x00' * 20, 0, 4)
        history = History()
        rng = random.Random(42)
        ops.glitch_randomize(state, history=history, rng=rng)
        self.assertTrue(history.can_undo())

    def test_randomize_without_selection_does_nothing(self):
        state = make_state(b'\x00' * 20)
        original = bytes(state.current)
        ops.glitch_randomize(state)
        self.assertEqual(bytes(state.current), original)

    def test_randomize_correct_length(self):
        data = b'\x00' * 20
        state = make_state(data, 0, 9)
        rng = random.Random(0)
        ops.glitch_randomize(state, rng=rng)
        self.assertEqual(len(state.current), len(data))


class TestGlitchInvert(unittest.TestCase):
    """ops.glitch_invert"""

    def test_invert_flips_bits(self):
        state = make_state(b'\xFF\x00\xAA', 0, 2)
        ops.glitch_invert(state)
        self.assertEqual(bytes(state.current), b'\x00\xFF\x55')

    def test_invert_double_application_restores(self):
        original = b'\xDE\xAD\xBE\xEF'
        state = make_state(original, 0, 3)
        ops.glitch_invert(state)
        state.select(0, 3)
        ops.glitch_invert(state)
        self.assertEqual(bytes(state.current), original)

    def test_invert_pushes_history(self):
        state = make_state(b'\xFF\x00', 0, 1)
        history = History()
        ops.glitch_invert(state, history=history)
        self.assertTrue(history.can_undo())

    def test_invert_without_selection_does_nothing(self):
        state = make_state(b'\xFF\x00')
        ops.glitch_invert(state)
        self.assertEqual(bytes(state.current), b'\xFF\x00')


class TestGlitchZero(unittest.TestCase):
    """ops.glitch_zero"""

    def test_zero_clears_selection(self):
        state = make_state(b'\xFF' * 10, 2, 7)
        ops.glitch_zero(state)
        self.assertEqual(bytes(state.current[2:8]), b'\x00' * 6)

    def test_zero_does_not_affect_outside(self):
        data = b'\xFF' * 10
        state = make_state(data, 2, 7)
        ops.glitch_zero(state)
        self.assertEqual(bytes(state.current[:2]), b'\xFF\xFF')
        self.assertEqual(bytes(state.current[8:]), b'\xFF\xFF')

    def test_zero_pushes_history(self):
        state = make_state(b'\xFF' * 10, 0, 9)
        history = History()
        ops.glitch_zero(state, history=history)
        self.assertTrue(history.can_undo())

    def test_zero_without_selection_does_nothing(self):
        state = make_state(b'\xFF' * 10)
        ops.glitch_zero(state)
        self.assertEqual(bytes(state.current), b'\xFF' * 10)


class TestWhitespaceInject(unittest.TestCase):
    """ops.whitespace_inject"""

    def test_injects_correct_count(self):
        state = make_state(b'\x01' * 20)
        rng = random.Random(0)
        inserted = ops.whitespace_inject(state, count=3, rng=rng)
        self.assertEqual(inserted, 3)
        self.assertEqual(len(state.current), 23)

    def test_injected_bytes_are_whitespace(self):
        state = make_state(b'\x01' * 20)
        rng = random.Random(7)
        ops.whitespace_inject(state, count=10, rng=rng)
        for b in state.current:
            if b not in (0x01, 0x09, 0x0A, 0x20):
                self.fail(f"Unexpected byte 0x{b:02X} in result")

    def test_inject_pushes_history(self):
        state = make_state(b'\x01' * 20)
        history = History()
        rng = random.Random(0)
        ops.whitespace_inject(state, history=history, count=1, rng=rng)
        self.assertTrue(history.can_undo())

    def test_inject_zero_count_returns_zero(self):
        state = make_state(b'\x01' * 10)
        inserted = ops.whitespace_inject(state, count=0)
        self.assertEqual(inserted, 0)


class TestRepeatChunks(unittest.TestCase):
    """ops.repeat_chunks"""

    def test_increases_length(self):
        state = make_state(b'\xAA\xBB\xCC\xDD\xEE' * 4)
        original_len = len(state.current)
        rng = random.Random(0)
        inserted = ops.repeat_chunks(state, size=2, repeats=3, rng=rng)
        self.assertGreater(len(state.current), original_len)
        self.assertGreater(inserted, 0)

    def test_pushes_history_on_change(self):
        state = make_state(b'\xAA' * 20)
        history = History()
        rng = random.Random(1)
        ops.repeat_chunks(state, history=history, size=2, repeats=1, rng=rng)
        self.assertTrue(history.can_undo())

    def test_zero_size_returns_zero(self):
        state = make_state(b'\xAA' * 10)
        result = ops.repeat_chunks(state, size=0, repeats=1)
        self.assertEqual(result, 0)


class TestPatternInject(unittest.TestCase):
    """ops.pattern_inject"""

    def test_injects_pattern(self):
        pattern = b'\xDE\xAD'
        state = make_state(b'\x00' * 10)
        rng = random.Random(0)
        inserted = ops.pattern_inject(state, pattern=pattern, count=2, rng=rng)
        self.assertEqual(inserted, 2)
        self.assertEqual(len(state.current), 14)

    def test_pattern_bytes_present_in_result(self):
        pattern = b'\xBE\xEF'
        state = make_state(b'\x00' * 20)
        rng = random.Random(3)
        ops.pattern_inject(state, pattern=pattern, count=3, rng=rng)
        data = bytes(state.current)
        self.assertIn(pattern, data)

    def test_empty_pattern_returns_zero(self):
        state = make_state(b'\x00' * 10)
        result = ops.pattern_inject(state, pattern=b'', count=1)
        self.assertEqual(result, 0)

    def test_pushes_history(self):
        state = make_state(b'\x00' * 10)
        history = History()
        rng = random.Random(0)
        ops.pattern_inject(state, history=history, pattern=b'\xFF', count=1, rng=rng)
        self.assertTrue(history.can_undo())


class TestShuffleBlocks(unittest.TestCase):
    """ops.shuffle_blocks"""

    def test_shuffle_changes_order(self):
        # Χρησιμοποιούμε αρκετά μεγάλο block για να βεβαιωθούμε ότι γίνεται shuffle
        data = bytes(range(256)) * 3  # 768 bytes
        state = make_state(data, 0, len(data) - 1)
        rng = random.Random(99)
        ops.shuffle_blocks(state, block_size=16, rng=rng)
        self.assertNotEqual(bytes(state.current), data)

    def test_shuffle_preserves_length(self):
        data = b'\xAA\xBB\xCC\xDD' * 50
        state = make_state(data, 0, len(data) - 1)
        rng = random.Random(0)
        ops.shuffle_blocks(state, block_size=4, rng=rng)
        self.assertEqual(len(state.current), len(data))

    def test_shuffle_preserves_byte_set(self):
        data = b'\xAA\xBB\xCC\xDD' * 10
        state = make_state(data, 0, len(data) - 1)
        rng = random.Random(7)
        ops.shuffle_blocks(state, block_size=4, rng=rng)
        self.assertEqual(sorted(state.current), sorted(data))

    def test_shuffle_pushes_history(self):
        data = bytes(range(256)) * 2
        state = make_state(data, 0, len(data) - 1)
        history = History()
        rng = random.Random(42)
        ops.shuffle_blocks(state, history=history, block_size=8, rng=rng)
        self.assertTrue(history.can_undo())

    def test_shuffle_zero_block_size_returns_zero(self):
        state = make_state(b'\xAA' * 20)
        result = ops.shuffle_blocks(state, block_size=0)
        self.assertEqual(result, 0)


class TestReverseBlocks(unittest.TestCase):
    """ops.reverse_blocks"""

    def test_reverse_single_byte_blocks(self):
        data = b'\x01\x02\x03\x04'
        state = make_state(data, 0, 3)
        ops.reverse_blocks(state, block_size=1)
        self.assertEqual(bytes(state.current), b'\x01\x02\x03\x04')

    def test_reverse_two_byte_blocks(self):
        data = b'\x01\x02\x03\x04'
        state = make_state(data, 0, 3)
        ops.reverse_blocks(state, block_size=2)
        # Κάθε 2-byte block αντιστρέφεται: [02 01] [04 03]
        self.assertEqual(bytes(state.current), b'\x02\x01\x04\x03')

    def test_reverse_preserves_length(self):
        data = b'\xAA\xBB\xCC\xDD' * 5
        state = make_state(data, 0, len(data) - 1)
        ops.reverse_blocks(state, block_size=4)
        self.assertEqual(len(state.current), len(data))

    def test_reverse_pushes_history(self):
        data = b'\x01\x02\x03\x04'
        state = make_state(data, 0, 3)
        history = History()
        ops.reverse_blocks(state, history=history, block_size=2)
        self.assertTrue(history.can_undo())

    def test_reverse_without_selection_works_on_body(self):
        # Χωρίς selection, reverse εφαρμόζεται στα bytes μετά τη θέση 512
        data = b'\x00' * 512 + b'\x01\x02\x03\x04'
        state = make_state(data)
        ops.reverse_blocks(state, block_size=2)
        self.assertEqual(bytes(state.current[512:]), b'\x02\x01\x04\x03')


class TestHexPatternReplace(unittest.TestCase):
    """ops.hex_pattern_replace"""

    def test_exact_pattern_replaced(self):
        data = b'\xDE\xAD\xBE\xEF' * 3
        state = make_state(data, 0, len(data) - 1)
        count = ops.hex_pattern_replace(state, pattern="DE AD BE EF", replace=b'\x00\x00\x00\x00')
        self.assertGreater(count, 0)
        self.assertNotIn(b'\xDE\xAD\xBE\xEF', bytes(state.current[:len(data)]))

    def test_wildcard_pattern(self):
        # .. αντιστοιχεί σε οποιοδήποτε byte
        data = b'\x01\xFF\x03\x01\xAA\x03'
        state = make_state(data, 0, len(data) - 1)
        count = ops.hex_pattern_replace(state, pattern="01 .. 03", replace=b'\x00\x00\x00')
        self.assertGreater(count, 0)

    def test_no_match_returns_zero(self):
        data = b'\x00' * 20
        state = make_state(data, 0, 19)
        count = ops.hex_pattern_replace(state, pattern="FF FF", replace=b'\x00\x00')
        self.assertEqual(count, 0)
        self.assertEqual(bytes(state.current), data)

    def test_pushes_history_on_change(self):
        data = b'\xAA\xBB' * 10
        state = make_state(data, 0, len(data) - 1)
        history = History()
        ops.hex_pattern_replace(state, history=history, pattern="AA BB", replace=b'\x00\x00')
        self.assertTrue(history.can_undo())

    def test_empty_pattern_returns_zero(self):
        state = make_state(b'\xFF' * 10)
        result = ops.hex_pattern_replace(state, pattern="", replace=b'\x00')
        self.assertEqual(result, 0)

    def test_odd_length_pattern_raises(self):
        state = make_state(b'\xFF' * 10)
        with self.assertRaises(ValueError):
            ops.hex_pattern_replace(state, pattern="A", replace=b'\x00')


# ===========================================================================
# 4.  state.py
# ===========================================================================

class TestAppStateLoad(unittest.TestCase):
    """AppState.load"""

    def test_load_sets_original_and_current(self):
        state = AppState()
        data = b'\x01\x02\x03'
        state.load("test.bin", data)
        self.assertEqual(state.original, data)
        self.assertEqual(bytes(state.current), data)

    def test_load_sets_fname(self):
        state = AppState()
        state.load("myfile.jpg", b'\xFF\xD8\xFF')
        self.assertEqual(state.fname, "myfile.jpg")

    def test_load_none_data(self):
        state = AppState()
        state.load("empty.bin", None)
        self.assertIsNone(state.original)
        self.assertEqual(bytes(state.current), b'')

    def test_load_clears_selection(self):
        state = AppState()
        state.load(None, b'\x00' * 20)
        state.select(2, 10)
        state.load(None, b'\x00' * 20)
        self.assertTrue(state.selection.is_empty())

    def test_load_resets_last_edit_pos(self):
        state = AppState()
        state.load(None, b'\x00' * 10)
        state.set_bytes(5, b'\xFF', replace_len=1)
        state.load(None, b'\x00' * 10)
        self.assertIsNone(state.last_edit_pos)


class TestAppStateIsDirty(unittest.TestCase):
    """AppState.is_dirty"""

    def test_not_dirty_after_load(self):
        state = make_state(b'\x01\x02\x03')
        self.assertFalse(state.is_dirty())

    def test_dirty_after_modification(self):
        state = make_state(b'\x01\x02\x03')
        state.set_bytes(0, b'\xFF', replace_len=1)
        self.assertTrue(state.is_dirty())

    def test_not_dirty_after_revert(self):
        state = make_state(b'\x01\x02\x03')
        state.set_bytes(0, b'\xFF', replace_len=1)
        state.set_bytes(0, b'\x01', replace_len=1)  # επαναφορά
        self.assertFalse(state.is_dirty())

    def test_dirty_none_original(self):
        state = AppState()
        self.assertFalse(state.is_dirty())


class TestAppStateClampOffset(unittest.TestCase):
    """AppState.clamp_offset"""

    def test_clamp_within_bounds(self):
        state = make_state(b'\x00' * 10)
        self.assertEqual(state.clamp_offset(5), 5)

    def test_clamp_below_zero(self):
        state = make_state(b'\x00' * 10)
        self.assertEqual(state.clamp_offset(-5), 0)

    def test_clamp_above_max(self):
        state = make_state(b'\x00' * 10)
        self.assertEqual(state.clamp_offset(100), 9)  # len-1

    def test_clamp_empty_state(self):
        state = AppState()
        self.assertEqual(state.clamp_offset(5), 0)


class TestAppStateSetBytes(unittest.TestCase):
    """AppState.set_bytes"""

    def test_overwrite_bytes(self):
        state = make_state(b'\x00\x00\x00\x00\x00')
        state.set_bytes(1, b'\xFF\xFF', replace_len=2)
        self.assertEqual(bytes(state.current), b'\x00\xFF\xFF\x00\x00')

    def test_insert_bytes_extends(self):
        state = make_state(b'\x01\x02\x03')
        state.set_bytes(1, b'\xAA\xBB', replace_len=0)
        # 0 replace_len → insert (current behaves like replace 0 bytes with 2)
        self.assertIn(b'\xAA\xBB', bytes(state.current))

    def test_negative_start_raises(self):
        state = make_state(b'\x00' * 5)
        with self.assertRaises(ValueError):
            state.set_bytes(-1, b'\xFF', replace_len=1)

    def test_none_start_raises(self):
        state = make_state(b'\x00' * 5)
        with self.assertRaises((ValueError, TypeError)):
            state.set_bytes(None, b'\xFF', replace_len=1)

    def test_last_edit_pos_updated(self):
        state = make_state(b'\x00' * 10)
        state.set_bytes(5, b'\xFF', replace_len=1)
        self.assertEqual(state.last_edit_pos, 5)


class TestAppStateSelectionAndClamp(unittest.TestCase):
    """AppState.select / get_selection_range / clamp_range"""

    def test_select_and_get_range(self):
        state = make_state(b'\x00' * 20)
        state.select(3, 10)
        result = state.get_selection_range()
        self.assertEqual(result, (3, 10))

    def test_get_selection_range_empty(self):
        state = make_state(b'\x00' * 20)
        self.assertIsNone(state.get_selection_range())

    def test_selection_inverted_returns_sorted(self):
        state = make_state(b'\x00' * 20)
        state.select(10, 3)
        result = state.get_selection_range()
        self.assertEqual(result, (3, 10))

    def test_clamp_range_valid(self):
        state = make_state(b'\x00' * 20)
        self.assertEqual(state.clamp_range(2, 8), (2, 8))

    def test_clamp_range_inverted(self):
        state = make_state(b'\x00' * 20)
        start, end = state.clamp_range(15, 5)
        self.assertLessEqual(start, end)

    def test_reset_selection_clears(self):
        state = make_state(b'\x00' * 20)
        state.select(0, 5)
        state.reset_selection()
        self.assertIsNone(state.get_selection_range())


# ===========================================================================
# Entry point
# ===========================================================================

def run_summary():
    """Εκτυπώνει σύνοψη αποτελεσμάτων με πίνακα test groups."""
    loader = unittest.TestLoader()
    groups = [
        ("formats – detect_format",        TestDetectFormat),
        ("formats – printable_latin1_str", TestPrintableLatin1Str),
        ("formats – ensure_magic_bytes",   TestEnsureMagicBytes),
        ("formats – get_format_extension", TestGetFormatExtension),
        ("formats – decode/encode_bytes",  TestDecodeEncodeBytes),
        ("history – push/undo/redo/clear", TestHistoryPushUndoRedo),
        ("history – get_edit_highlights",  TestHistoryGetEditHighlights),
        ("ops – glitch_randomize",         TestGlitchRandomize),
        ("ops – glitch_invert",            TestGlitchInvert),
        ("ops – glitch_zero",              TestGlitchZero),
        ("ops – whitespace_inject",        TestWhitespaceInject),
        ("ops – repeat_chunks",            TestRepeatChunks),
        ("ops – pattern_inject",           TestPatternInject),
        ("ops – shuffle_blocks",           TestShuffleBlocks),
        ("ops – reverse_blocks",           TestReverseBlocks),
        ("ops – hex_pattern_replace",      TestHexPatternReplace),
        ("state – load",                   TestAppStateLoad),
        ("state – is_dirty",               TestAppStateIsDirty),
        ("state – clamp_offset",           TestAppStateClampOffset),
        ("state – set_bytes",              TestAppStateSetBytes),
        ("state – selection/clamp_range",  TestAppStateSelectionAndClamp),
    ]

    total_passed = total_failed = total_errors = 0
    print("\n" + "=" * 70)
    print(f"{'Group':<40} {'Tests':>6} {'Passed':>7} {'Failed':>7}")
    print("=" * 70)

    all_results = []
    for label, cls in groups:
        suite = loader.loadTestsFromTestCase(cls)
        runner = unittest.TextTestRunner(stream=open(os.devnull, "w"), verbosity=0)
        result = runner.run(suite)
        n = result.testsRun
        f = len(result.failures) + len(result.errors)
        p = n - f
        total_passed += p
        total_failed += f
        all_results.append((label, n, p, f, result))
        status = "✓" if f == 0 else "✗"
        print(f"  {status} {label:<38} {n:>6} {p:>7} {f:>7}")

    print("=" * 70)
    total = total_passed + total_failed
    print(f"  {'ΣΥΝΟΛΟ':<40} {total:>6} {total_passed:>7} {total_failed:>7}")
    print("=" * 70)

    # Εκτύπωση αστοχιών αν υπάρχουν
    for label, n, p, f, result in all_results:
        if result.failures or result.errors:
            print(f"\n{'─'*60}")
            print(f"ΑΣΤΟΧΙΕΣ – {label}")
            for test, trace in result.failures + result.errors:
                print(f"\n  ► {test}")
                # Τελευταία γραμμή του traceback
                lines = [l for l in trace.splitlines() if l.strip()]
                print(f"    {lines[-1]}")

    print()
    return total_failed == 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Databender Unit Tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Λεπτομερής έξοδος unittest")
    parser.add_argument("--summary", "-s", action="store_true", help="Εκτύπωση πίνακα σύνοψης (default)")
    args = parser.parse_args()

    if args.verbose:
        unittest.main(argv=[""], verbosity=2, exit=True)
    else:
        ok = run_summary()
        sys.exit(0 if ok else 1)