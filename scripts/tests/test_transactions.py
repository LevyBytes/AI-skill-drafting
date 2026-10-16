import unittest
from support import prepared, spec
from drafting.preparation import load
from drafting.render import render
from drafting.storage import inventory, read_json, tree, tree_digest
from drafting.transactions import apply, deploy, rollback


class Transactions(unittest.TestCase):
    def test_fresh_roundtrip_git_preserved(self):
        root = prepared()
        git = root / "live/.git"
        git.mkdir(); (git / "config").write_bytes(b"fixture git metadata\n")
        report = apply(root / "work")
        self.assertEqual(tree(root / "live"), {})
        deploy(root / "work", root / "live", report["digest"], "Fixture owner approval")
        self.assertEqual(tree(root / "live"), tree(root / "proposal"))
        rollback(root / "work", "Fixture rollback approval")
        self.assertEqual(tree(root / "live"), {})
        self.assertEqual((git / "config").read_bytes(), b"fixture git metadata\n")

    def test_repair_roundtrip(self):
        before, _ = render(spec(content="Original prose."))
        after, _ = render(spec(content="Reviewed, repaired prose."))
        root = prepared(before, after)
        report = apply(root / "work")
        deploy(root / "work", root / "live", report["digest"], "Fixture approval")
        self.assertEqual(tree(root / "live"), after)
        rollback(root / "work", "Fixture rollback")
        self.assertEqual(tree(root / "live"), before)

    def test_apply_resume(self):
        root = prepared()
        with self.assertRaises(RuntimeError):
            apply(root / "work", stop_after=2)
        self.assertTrue(apply(root / "work")["passed"])

    def test_deploy_and_rollback_resume(self):
        root = prepared()
        report = apply(root / "work")
        with self.assertRaises(RuntimeError):
            deploy(root / "work", root / "live", report["digest"], "Fixture approval", stop_after=2)
        deploy(root / "work", root / "live", report["digest"], "Fixture approval")
        with self.assertRaises(RuntimeError):
            rollback(root / "work", "Fixture rollback", stop_after=2)
        rollback(root / "work", "Fixture rollback")
        self.assertEqual(tree(root / "live"), {})

    def test_wrong_approval_no_mutation(self):
        root = prepared(); apply(root / "work")
        with self.assertRaisesRegex(ValueError, "Approval"):
            deploy(root / "work", root / "live", "bad", "Fixture approval")
        self.assertEqual(tree(root / "live"), {})
        self.assertFalse((root / "work/rollback").exists())

    def test_input_drift(self):
        root = prepared()
        (root / "live/owner-edit.txt").write_bytes(b"Owner edit")
        with self.assertRaisesRegex(ValueError, "drift"):
            apply(root / "work")

    def test_candidate_drift(self):
        root = prepared(); report = apply(root / "work")
        (root / "work/candidate/example-skill/SKILL.md").write_bytes(b"Changed")
        with self.assertRaisesRegex(ValueError, "Candidate drift"):
            deploy(root / "work", root / "live", report["digest"], "Fixture approval")

    def test_completed_apply_drift(self):
        root = prepared(); apply(root / "work")
        (root / "work/candidate/example-skill/SKILL.md").unlink()
        with self.assertRaisesRegex(ValueError, "Completed candidate drift"):
            apply(root / "work")

    def test_frozen_requirements_and_manifest(self):
        for artifact in ("REQUIREMENTS.md", "manifest.json", "proposed/SKILL.md"):
            with self.subTest(artifact=artifact):
                root = prepared()
                path = root / "work" / artifact
                path.write_bytes(path.read_bytes() + b" ")
                # JSON whitespace is semantically canonical; changing a parsed task is tested separately.
                if artifact == "manifest.json":
                    path.write_bytes(path.read_bytes().replace(b'"name": "example-skill"', b'"name": "changed-skill"'))
                with self.assertRaises(ValueError):
                    load(root / "work")

    def test_post_deploy_edit_preserved(self):
        root = prepared(); report = apply(root / "work")
        deploy(root / "work", root / "live", report["digest"], "Fixture approval")
        (root / "live/SKILL.md").write_bytes(b"Owner edit")
        with self.assertRaisesRegex(ValueError, "Post-deployment edits"):
            rollback(root / "work", "Fixture rollback")
        self.assertEqual((root / "live/SKILL.md").read_bytes(), b"Owner edit")

    def test_unrelated_empty_folder_preserved(self):
        root = prepared(); report = apply(root / "work")
        (root / "live/owner-empty-folder").mkdir()
        deploy(root / "work", root / "live", report["digest"], "Fixture approval")
        self.assertTrue((root / "live/owner-empty-folder").is_dir())
        rollback(root / "work", "Fixture rollback")
        self.assertTrue((root / "live/owner-empty-folder").is_dir())

    def test_concurrent_writer_lock(self):
        root = prepared()
        (root / "work/transaction.lock").write_text("other process")
        with self.assertRaisesRegex(ValueError, "lock exists"):
            apply(root / "work")

    def test_interrupted_completed_file_cannot_be_reverted(self):
        root = prepared()
        with self.assertRaises(RuntimeError):
            apply(root / "work", stop_after=2)
        import json
        first = json.loads((root / "work/apply.jsonl").read_text().splitlines()[0])
        path = root / "work/candidate/example-skill" / first["path"]
        path.unlink()
        with self.assertRaisesRegex(ValueError, "Completed outcome drift"):
            apply(root / "work")

    def test_pending_atomic_write_preserved(self):
        from drafting.storage import atomic
        root = prepared()
        (root / "note.writing").write_bytes(b"Unresolved bytes")
        with self.assertRaisesRegex(ValueError, "interrupted write"):
            atomic(root / "note", b"New bytes")
        self.assertEqual((root / "note.writing").read_bytes(), b"Unresolved bytes")
        self.assertFalse((root / "note").exists())

    def test_transient_replace_denial_retries_owned_write(self):
        from unittest.mock import patch
        from drafting.storage import atomic
        import os
        root = prepared()
        original = os.replace
        attempts = []
        def transient(source, destination):
            attempts.append(1)
            if len(attempts) < 3:
                raise PermissionError("Transient fixture sharing violation")
            original(source, destination)
        with patch("drafting.storage.os.replace", transient):
            atomic(root / "result", b"Complete")
        self.assertEqual(len(attempts), 3)
        self.assertEqual((root / "result").read_bytes(), b"Complete")
