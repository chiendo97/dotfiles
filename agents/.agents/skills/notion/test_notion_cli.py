from __future__ import annotations

import csv
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from unittest.mock import patch

import typer
from typer.testing import CliRunner

import notion_cli


class NotionCliCreateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_project_config_keeps_sprint_fields(self) -> None:
        proj = notion_cli.ProjectConfig.model_validate({
            "database_id": "tickets-db",
            "tickets_data_source_id": "tickets-ds",
            "sprints_data_source_id": "sprints-ds",
            "prop_sprint": "Sprint",
            "prop_sprint_date": "Start Date",
        })

        self.assertEqual(proj.tickets_data_source_id, "tickets-ds")
        self.assertEqual(proj.sprints_data_source_id, "sprints-ds")
        self.assertEqual(proj.prop_sprint, "Sprint")
        self.assertEqual(proj.prop_sprint_date, "Start Date")

    def test_config_keeps_default_creator_alias(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbooks",
            "default_creator_alias": "owner",
        })

        self.assertEqual(config.default_creator_alias, "owner")

    def test_skill_config_routes_data_platform_to_live_sources(self) -> None:
        skill_dir = Path(notion_cli.__file__).resolve().parent
        config = notion_cli.load_config(str(skill_dir / "notion.yaml"))
        proj = config.projects["data-platform"]

        self.assertEqual(proj.database_id, "fee2cfcc-3b9d-4f93-aed4-f98348053a65")
        self.assertEqual(proj.tickets_data_source_id, "b2c239bb-c390-4c01-8905-d9e5be564829")
        self.assertEqual(proj.sprints_data_source_id, "fc6d86d6-1383-4673-a33d-ed2a46dc9abc")
        self.assertEqual(proj.epics_database_id, "31fd67a3-7e1d-81c4-821f-e921aa006bf6")
        self.assertEqual(proj.ticket_status_type, "select")
        self.assertEqual(proj.status_name_overrides, {"In progress": "In Progress"})

    def test_default_config_paths_use_skill_local_config_not_claude_boy(self) -> None:
        skill_dir = Path(notion_cli.__file__).resolve().parent

        self.assertEqual(notion_cli.DEFAULT_CONFIG_PATHS, [skill_dir / "notion.yaml", Path("./config/notion.yaml")])
        self.assertNotIn("claude-boy", "\n".join(str(path) for path in notion_cli.DEFAULT_CONFIG_PATHS))

    def test_find_current_sprint_queries_sprint_data_source(self) -> None:
        proj = notion_cli.ProjectConfig.model_validate({
            "database_id": "tickets-db",
            "sprints_data_source_id": "sprints-ds",
            "prop_sprint_date": "Start Date",
        })

        with patch.object(notion_cli, "_query_data_source", return_value=[{"id": "sprint-page"}]) as query:
            sprint_id = notion_cli._find_current_sprint_id(proj, date(2026, 5, 8))

        self.assertEqual(sprint_id, "sprint-page")
        query.assert_called_once_with(
            "sprints-ds",
            {
                "page_size": 1,
                "filter": {"property": "Start Date", "date": {"on_or_before": "2026-05-08"}},
                "sorts": [{"property": "Start Date", "direction": "descending"}],
            },
        )

    def test_find_current_sprint_requires_configured_sprint_source(self) -> None:
        proj = notion_cli.ProjectConfig.model_validate({"database_id": "tickets-db"})

        with redirect_stderr(io.StringIO()), self.assertRaises(typer.Exit):
            notion_cli._find_current_sprint_id(proj, date(2026, 5, 8))

    def test_find_epic_filters_only_existing_title_properties(self) -> None:
        page = {
            "id": "epic-page",
            "properties": {
                "Epic": {"title": [{"plain_text": "Internal tools"}]},
            },
        }

        with (
            patch.object(
                notion_cli,
                "_get_database_properties",
                return_value={"Epic": {"type": "title"}, "Status": {"type": "status"}},
            ),
            patch.object(notion_cli, "_query_database", return_value=[page]) as query,
        ):
            epic_id = notion_cli._find_epic_id("epics-db", "Internal tools")

        self.assertEqual(epic_id, "epic-page")
        query.assert_called_once_with(
            "epics-db",
            {"filter": {"property": "Epic", "title": {"equals": "Internal tools"}}},
        )

    def test_create_defaults_to_creator_and_current_sprint(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbooks",
            "default_creator_alias": "owner",
            "projects": {
                "genbooks": {
                    "database_id": "tickets-db",
                    "tickets_data_source_id": "tickets-ds",
                    "epics_database_id": "epics-db",
                    "sprints_data_source_id": "sprints-ds",
                    "prop_epic": "Epics",
                    "prop_sprint": "Sprint",
                    "prop_title_id": "title",
                    "prop_assignee_id": "assignee-prop",
                    "prop_sprint_id": "sprint-prop",
                    "prop_epic_id": "epics-prop",
                    "prop_priority_id": "priority-prop",
                    "prop_status_id": "status-prop",
                }
            },
            "users": {"owner": "creator-user-id"},
        })

        created_page = {
            "id": "ticket-page",
            "url": "https://notion.so/ticket-page",
            "properties": {},
        }

        with (
            patch.object(notion_cli, "get_config", return_value=config),
            patch.object(notion_cli, "_find_epic_id", return_value="epic-page"),
            patch.object(notion_cli, "_find_current_sprint_id", return_value="sprint-page"),
            patch.object(notion_cli, "_post", return_value=created_page) as post,
            redirect_stdout(io.StringIO()),
        ):
            notion_cli.create(title="Fix auth bug", epic="Sprint Planning v2")

        post.assert_called_once()
        _, payload, notion_version = post.call_args.args
        self.assertEqual(notion_version, notion_cli.DATA_SOURCE_NOTION_VERSION)
        self.assertEqual(payload["parent"], {"data_source_id": "tickets-ds"})
        self.assertEqual(payload["properties"]["title"], {"title": [{"text": {"content": "Fix auth bug"}}]})
        self.assertEqual(payload["properties"]["assignee-prop"], {"people": [{"id": "creator-user-id"}]})
        self.assertEqual(payload["properties"]["sprint-prop"], {"relation": [{"id": "sprint-page"}]})
        self.assertEqual(payload["properties"]["epics-prop"], {"relation": [{"id": "epic-page"}]})

    def test_create_uses_configured_property_ids_without_schema_lookup(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbooks",
            "default_creator_alias": "owner",
            "projects": {
                "genbooks": {
                    "database_id": "tickets-db",
                    "tickets_data_source_id": "tickets-ds",
                    "epics_database_id": "epics-db",
                    "sprints_data_source_id": "sprints-ds",
                    "prop_title_id": "title",
                    "prop_assignee_id": "assignee-prop",
                    "prop_sprint_id": "sprint-prop",
                    "prop_epic_id": "epics-prop",
                    "prop_priority_id": "priority-prop",
                    "prop_status_id": "status-prop",
                }
            },
            "users": {"owner": "creator-user-id"},
        })

        created_page = {
            "id": "ticket-page",
            "url": "https://notion.so/ticket-page",
            "properties": {},
        }

        with (
            patch.object(notion_cli, "get_config", return_value=config),
            patch.object(notion_cli, "_find_epic_id", return_value="epic-page"),
            patch.object(notion_cli, "_find_current_sprint_id", return_value="sprint-page"),
            patch.object(notion_cli, "_request", return_value={}) as request,
            patch.object(notion_cli, "_post", return_value=created_page) as post,
            redirect_stdout(io.StringIO()),
        ):
            notion_cli.create(title="Fix auth bug", epic="Sprint Planning v2", status=notion_cli.Status.BACKLOG)

        request.assert_not_called()
        post.assert_called_once()
        _, payload, _notion_version = post.call_args.args
        self.assertEqual(payload["properties"]["title"], {"title": [{"text": {"content": "Fix auth bug"}}]})
        self.assertEqual(payload["properties"]["assignee-prop"], {"people": [{"id": "creator-user-id"}]})
        self.assertEqual(payload["properties"]["sprint-prop"], {"relation": [{"id": "sprint-page"}]})
        self.assertEqual(payload["properties"]["epics-prop"], {"relation": [{"id": "epic-page"}]})
        self.assertEqual(payload["properties"]["priority-prop"], {"select": {"name": "Medium"}})
        self.assertEqual(payload["properties"]["status-prop"], {"status": {"name": "Backlog"}})

    def test_create_uses_project_status_type_and_name_override(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "data-platform",
            "default_creator_alias": "owner",
            "projects": {
                "data-platform": {
                    "database_id": "tickets-db",
                    "tickets_data_source_id": "tickets-ds",
                    "epics_database_id": "epics-db",
                    "sprints_data_source_id": "sprints-ds",
                    "prop_title_id": "title",
                    "prop_assignee_id": "assignee-prop",
                    "prop_sprint_id": "sprint-prop",
                    "prop_epic_id": "epics-prop",
                    "prop_priority_id": "priority-prop",
                    "prop_status_id": "status-prop",
                    "ticket_status_type": "select",
                    "status_name_overrides": {"In progress": "In Progress"},
                }
            },
            "users": {"owner": "creator-user-id"},
        })

        with (
            patch.object(notion_cli, "get_config", return_value=config),
            patch.object(notion_cli, "_find_epic_id", return_value="epic-page"),
            patch.object(notion_cli, "_find_current_sprint_id", return_value="sprint-page"),
            patch.object(
                notion_cli,
                "_post",
                return_value={"id": "ticket-page", "url": "https://notion.so/ticket-page", "properties": {}},
            ) as post,
            redirect_stdout(io.StringIO()),
        ):
            notion_cli.create(
                title="Fix auth bug",
                epic="Build Entity Registry",
                status=notion_cli.Status.IN_PROGRESS,
            )

        _, payload, _notion_version = post.call_args.args
        self.assertEqual(
            payload["properties"]["status-prop"],
            {"select": {"name": "In Progress"}},
        )

    def test_create_requires_configured_property_ids_for_data_source_projects(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbooks",
            "default_creator_alias": "owner",
            "projects": {
                "genbooks": {
                    "database_id": "tickets-db",
                    "tickets_data_source_id": "tickets-ds",
                    "epics_database_id": "epics-db",
                    "sprints_data_source_id": "sprints-ds",
                    "prop_title_id": "title",
                    "prop_assignee_id": "assignee-prop",
                    "prop_sprint_id": "sprint-prop",
                    "prop_epic_id": "epics-prop",
                    "prop_priority_id": "priority-prop",
                }
            },
            "users": {"owner": "creator-user-id"},
        })
        stderr = io.StringIO()

        with (
            patch.object(notion_cli, "get_config", return_value=config),
            patch.object(notion_cli, "_find_epic_id", return_value="epic-page"),
            patch.object(notion_cli, "_find_current_sprint_id", return_value="sprint-page"),
            patch.object(notion_cli, "_request", return_value={}) as request,
            patch.object(notion_cli, "_post") as post,
            redirect_stderr(stderr),
            self.assertRaises(typer.Exit),
        ):
            notion_cli.create(title="Fix auth bug", epic="Sprint Planning v2", status=notion_cli.Status.BACKLOG)

        self.assertIn("missing create property id(s): prop_status_id", stderr.getvalue())
        request.assert_not_called()
        post.assert_not_called()

    def test_create_fails_before_post_when_epic_missing(self) -> None:
        result = self.runner.invoke(notion_cli.app, ["create", "--title", "Fix auth bug"])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Missing option", result.output)
        self.assertIn("--epic", result.output)

    def test_create_fails_before_post_when_epic_source_missing(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbooks",
            "default_creator_alias": "owner",
            "projects": {
                "genbooks": {
                    "database_id": "tickets-db",
                    "sprints_data_source_id": "sprints-ds",
                }
            },
            "users": {"owner": "creator-user-id"},
        })

        with (
            patch.object(notion_cli, "get_config", return_value=config),
            patch.object(notion_cli, "_find_current_sprint_id") as find_sprint,
            patch.object(notion_cli, "_post") as post,
            redirect_stderr(io.StringIO()),
            self.assertRaises(typer.Exit),
        ):
            notion_cli.create(title="Fix auth bug", epic="Sprint Planning v2")

        find_sprint.assert_not_called()
        post.assert_not_called()

    def test_create_fails_before_post_when_epic_not_found(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbooks",
            "default_creator_alias": "owner",
            "projects": {
                "genbooks": {
                    "database_id": "tickets-db",
                    "epics_database_id": "epics-db",
                    "sprints_data_source_id": "sprints-ds",
                }
            },
            "users": {"owner": "creator-user-id"},
        })

        with (
            patch.object(notion_cli, "get_config", return_value=config),
            patch.object(notion_cli, "_find_epic_id", return_value=None),
            patch.object(notion_cli, "_find_current_sprint_id") as find_sprint,
            patch.object(notion_cli, "_post") as post,
            redirect_stderr(io.StringIO()),
            self.assertRaises(typer.Exit),
        ):
            notion_cli.create(title="Fix auth bug", epic="Missing Epic")

        find_sprint.assert_not_called()
        post.assert_not_called()

    def test_create_fails_before_post_when_default_creator_missing(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbooks",
            "projects": {"genbooks": {"database_id": "tickets-db", "sprints_data_source_id": "sprints-ds"}},
            "users": {"cle": "creator-user-id"},
        })

        with (
            patch.object(notion_cli, "get_config", return_value=config),
            patch.object(notion_cli, "_post") as post,
            redirect_stderr(io.StringIO()),
            self.assertRaises(typer.Exit),
        ):
            notion_cli.create(title="Fix auth bug", epic="Sprint Planning v2")

        post.assert_not_called()

    def test_create_fails_before_post_when_creator_mapping_missing(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbooks",
            "default_creator_alias": "owner",
            "projects": {"genbooks": {"database_id": "tickets-db", "sprints_data_source_id": "sprints-ds"}},
            "users": {},
        })

        with (
            patch.object(notion_cli, "get_config", return_value=config),
            patch.object(notion_cli, "_post") as post,
            redirect_stderr(io.StringIO()),
            self.assertRaises(typer.Exit),
        ):
            notion_cli.create(title="Fix auth bug", epic="Sprint Planning v2")

        post.assert_not_called()


class NotionCliUpdateTests(unittest.TestCase):
    def test_update_uses_project_status_type_and_name_override(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbook-global",
            "projects": {
                "data-platform": {
                    "database_id": "tickets-db",
                    "ticket_status_type": "select",
                    "status_name_overrides": {"In progress": "In Progress"},
                }
            },
        })

        with (
            patch.object(notion_cli, "get_config", return_value=config),
            patch.object(notion_cli, "_resolve_page", return_value={"id": "ticket-page"}),
            patch.object(notion_cli, "_patch", return_value={"url": "https://notion.so/ticket"}) as patch_page,
            redirect_stdout(io.StringIO()),
        ):
            notion_cli.update(
                page_id="ticket-page",
                status=notion_cli.Status.IN_PROGRESS,
                project="data-platform",
            )

        patch_page.assert_called_once_with(
            "/pages/ticket-page",
            {"properties": {"Status": {"select": {"name": "In Progress"}}}},
        )

    def test_update_epic_resolves_project_epic_and_patches_relation_property(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbook-global",
            "projects": {
                "genbook-global": {
                    "database_id": "tickets-db",
                    "epics_database_id": "epics-db",
                    "prop_epic": "Epics",
                }
            },
        })

        with (
            patch.object(notion_cli, "get_config", return_value=config),
            patch.object(notion_cli, "_resolve_page", return_value={"id": "ticket-page"}),
            patch.object(notion_cli, "_find_epic_id", return_value="epic-page") as find_epic,
            patch.object(notion_cli, "_patch", return_value={"url": "https://notion.so/ticket"}) as patch_page,
            redirect_stdout(io.StringIO()),
        ):
            notion_cli.update(page_id="ticket-page", epic="Onboarding Amz Data", project="genbook-global")

        find_epic.assert_called_once_with("epics-db", "Onboarding Amz Data")
        patch_page.assert_called_once_with(
            "/pages/ticket-page",
            {"properties": {"Epics": {"relation": [{"id": "epic-page"}]}}},
        )

    def test_update_epic_fails_before_patch_when_epic_not_found(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbook-global",
            "projects": {
                "genbook-global": {
                    "database_id": "tickets-db",
                    "epics_database_id": "epics-db",
                    "prop_epic": "Epics",
                }
            },
        })

        with (
            patch.object(notion_cli, "get_config", return_value=config),
            patch.object(notion_cli, "_resolve_page", return_value={"id": "ticket-page"}),
            patch.object(notion_cli, "_find_epic_id", return_value=None),
            patch.object(notion_cli, "_patch") as patch_page,
            redirect_stderr(io.StringIO()),
            self.assertRaises(typer.Exit),
        ):
            notion_cli.update(page_id="ticket-page", epic="Missing Epic", project="genbook-global")

        patch_page.assert_not_called()

    def test_update_accepts_ticket_id_and_resolves_page(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbook-global",
            "projects": {"genbook-global": {"database_id": "tickets-db"}},
        })
        with (
            patch.object(notion_cli, "get_config", return_value=config),
            patch.object(
                notion_cli,
                "_resolve_page",
                return_value={"id": "real-uuid", "url": "https://notion.so/x"},
            ) as resolve_page,
            patch.object(notion_cli, "_patch", return_value={"id": "real-uuid", "url": "https://notion.so/x"}) as patch_page,
            redirect_stdout(io.StringIO()),
        ):
            notion_cli.update(page_id="GB-319", title="New title", project="genbook-global")

        resolve_page.assert_called_once_with("GB-319", config, "genbook-global")
        patch_page.assert_called_once_with(
            "/pages/real-uuid",
            {"properties": {"Name": {"title": [{"text": {"content": "New title"}}]}}},
        )

    def test_resolve_page_fetched_directly_for_uuid(self) -> None:
        config = notion_cli.Config.model_validate({})
        page = {"id": "real-uuid"}
        with (
            patch.object(notion_cli, "_get", return_value=page) as get_page,
        ):
            result = notion_cli._resolve_page("real-uuid", config)

        get_page.assert_called_once_with("/pages/real-uuid")
        self.assertEqual(result, page)

    def test_resolve_page_errors_when_ticket_id_not_found(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbook-global",
            "projects": {"genbook-global": {"database_id": "tickets-db"}},
        })
        with patch.object(notion_cli, "_query_database", return_value=[]):
            result = notion_cli._resolve_page("GB-999", config, "genbook-global")

        self.assertIsNone(result)

    def test_bulk_updates_each_resolved_ticket(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbook-global",
            "projects": {"genbook-global": {"database_id": "tickets-db"}},
        })
        pages = {"GB-1": {"id": "uuid-1"}, "GB-2": {"id": "uuid-2"}}

        def fake_resolve(ticket, cfg, project=None):
            return pages.get(ticket)

        with (
            patch.object(notion_cli, "get_config", return_value=config),
            patch.object(notion_cli, "_resolve_page", side_effect=fake_resolve) as resolve_page,
            patch.object(notion_cli, "_patch", return_value={}) as patch_page,
            redirect_stdout(io.StringIO()),
        ):
            with self.assertRaises(typer.Exit):
                notion_cli.bulk(["GB-1", "GB-9"], priority=notion_cli.Priority.HIGH, project="genbook-global")

        resolve_page.assert_any_call("GB-1", config, "genbook-global")
        self.assertEqual(patch_page.call_count, 1)
        patch_page.assert_called_once_with(
            "/pages/uuid-1",
            {"properties": {"Priority": {"select": {"name": "High"}}}},
        )

    def test_bulk_requires_at_least_one_field(self) -> None:
        config = notion_cli.Config.model_validate({})
        with (
            patch.object(notion_cli, "get_config", return_value=config),
            redirect_stderr(io.StringIO()),
            self.assertRaises(typer.Exit),
        ):
            notion_cli.bulk(["GB-1"])


class NotionCliAhWeekTests(unittest.TestCase):
    def test_week_range_defaults_to_monday_through_sunday(self) -> None:
        # 2026-09-18 is a Friday
        start, end = notion_cli._ah_week_range(None, None, today=date(2026, 9, 18))

        self.assertEqual((start, end), (date(2026, 9, 14), date(2026, 9, 20)))

    def test_week_range_uses_explicit_since_and_until(self) -> None:
        start, end = notion_cli._ah_week_range(date(2026, 9, 1), date(2026, 9, 19), today=date(2026, 9, 18))

        self.assertEqual((start, end), (date(2026, 9, 1), date(2026, 9, 19)))

    def test_week_range_rejects_until_before_since(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(typer.Exit):
            notion_cli._ah_week_range(date(2026, 9, 19), date(2026, 9, 1), today=date(2026, 9, 18))

    def test_mr_index_prefers_merged_and_most_recent(self) -> None:
        mrs = [
            {"title": "[SN-1] fix thing", "state": "opened", "web_url": "https://git/mrs/1", "updated_at": "2026-09-18T10:00:00Z"},
            {"title": "[SN-1] fix thing v2", "state": "merged", "web_url": "https://git/mrs/2", "updated_at": "2026-09-15T10:00:00Z"},
            {"title": "[SN-2] other", "state": "opened", "web_url": "https://git/mrs/3", "updated_at": "2026-09-10T10:00:00Z"},
            {"title": "[SN-2] other v2", "state": "opened", "web_url": "https://git/mrs/4", "updated_at": "2026-09-19T10:00:00Z"},
        ]

        index = notion_cli._build_mr_index(mrs)

        self.assertEqual(index["SN-1"], "https://git/mrs/2")
        self.assertEqual(index["SN-2"], "https://git/mrs/4")

    def test_ah_week_changes_detects_edited_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "ah.csv"
            base_path = notion_cli._ah_baseline_path(csv_path)
            notion_cli._write_csv(csv_path, [{"id": "SN-1", "status": "Review", "priority": "High", "ah": "1.0", "mr": "", "name": "x", "sort_date": "2026-09-14", "notion_url": ""}], notion_cli.AH_WEEK_CSV_COLUMNS)
            notion_cli._write_csv(base_path, [{"id": "SN-1", "status": "In progress", "priority": "High", "ah": "", "mr": "", "name": "x", "sort_date": "2026-09-14", "notion_url": ""}], notion_cli.AH_WEEK_CSV_COLUMNS + ["project"])

            changes = notion_cli._ah_week_changes(csv_path, base_path)

        self.assertEqual(changes, {"SN-1": {"status": ("In progress", "Review"), "ah": ("", "1.0")}})

    def test_ah_week_merge_keeps_user_edits_and_refreshes_blanks(self) -> None:
        pulled = [
            {"id": "SN-1", "name": "x", "status": "Done", "priority": "High", "ah": "", "mr": "https://git/mrs/9", "sort_date": "2026-09-14", "notion_url": "u", "project": "data-platform"},
            {"id": "SN-2", "name": "new", "status": "", "priority": "Medium", "ah": "", "mr": "", "sort_date": "2026-09-15", "notion_url": "u2", "project": "data-platform"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "ah.csv"
            base_path = notion_cli._ah_baseline_path(csv_path)
            # User edited SN-1 status (Done -> Review) and mr
            notion_cli._write_csv(csv_path, [{"id": "SN-1", "status": "Review", "priority": "High", "ah": "", "mr": "https://git/mrs/9", "name": "x", "sort_date": "2026-09-14", "notion_url": "u"}], notion_cli.AH_WEEK_CSV_COLUMNS)
            notion_cli._write_csv(base_path, [{"id": "SN-1", "status": "Done", "priority": "High", "ah": "", "mr": "https://git/mrs/9", "name": "x", "sort_date": "2026-09-14", "notion_url": "u", "project": "data-platform"}], notion_cli.AH_WEEK_CSV_COLUMNS + ["project"])

            csv_rows, base_rows = notion_cli._ah_week_merge(pulled, csv_path, base_path)

        by_id = {r["id"]: r for r in csv_rows}
        self.assertEqual(by_id["SN-1"]["status"], "Review")  # user edit kept
        self.assertEqual(by_id["SN-2"]["mr"], "")  # new row
        base_by_id = {r["id"]: r for r in base_rows}
        self.assertEqual(base_by_id["SN-1"]["status"], "Done")  # baseline keeps pulled value
        self.assertEqual(base_by_id["SN-2"]["project"], "data-platform")

    def test_ah_week_merge_keeps_mr_when_scan_skipped(self) -> None:
        pulled = [
            {"id": "SN-1", "name": "x", "status": "Done", "priority": "High", "ah": "", "mr": "", "sort_date": "2026-09-14", "notion_url": "u", "project": "data-platform"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "ah.csv"
            base_path = notion_cli._ah_baseline_path(csv_path)
            notion_cli._write_csv(csv_path, [{"id": "SN-1", "status": "Done", "priority": "High", "ah": "", "mr": "https://git/mrs/9", "name": "x", "sort_date": "2026-09-14", "notion_url": "u"}], notion_cli.AH_WEEK_CSV_COLUMNS)
            notion_cli._write_csv(base_path, [{"id": "SN-1", "status": "Done", "priority": "High", "ah": "", "mr": "https://git/mrs/9", "name": "x", "sort_date": "2026-09-14", "notion_url": "u", "project": "data-platform"}], notion_cli.AH_WEEK_CSV_COLUMNS + ["project"])

            csv_rows, _ = notion_cli._ah_week_merge(pulled, csv_path, base_path, scan_skipped=True)

        self.assertEqual({r["id"]: r["mr"] for r in csv_rows}["SN-1"], "https://git/mrs/9")

    def test_ah_week_merge_refreshes_non_editable_column(self) -> None:
        pulled = [
            {"id": "SN-1", "name": "renamed", "status": "Done", "priority": "High", "ah": "", "mr": "", "sort_date": "2026-09-16", "notion_url": "u2", "project": "data-platform"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "ah.csv"
            base_path = notion_cli._ah_baseline_path(csv_path)
            notion_cli._write_csv(csv_path, [{"id": "SN-1", "status": "Done", "priority": "High", "ah": "", "mr": "", "name": "edited", "sort_date": "2026-09-99", "notion_url": "old"}], notion_cli.AH_WEEK_CSV_COLUMNS)
            notion_cli._write_csv(base_path, [{"id": "SN-1", "status": "Done", "priority": "High", "ah": "", "mr": "", "name": "original", "sort_date": "2026-09-14", "notion_url": "u", "project": "data-platform"}], notion_cli.AH_WEEK_CSV_COLUMNS + ["project"])

            csv_rows, _ = notion_cli._ah_week_merge(pulled, csv_path, base_path)

        row = {r["id"]: r for r in csv_rows}["SN-1"]
        self.assertEqual(row["name"], "renamed")  # non-editable refreshed from pull
        self.assertEqual(row["sort_date"], "2026-09-16")

    def test_ah_week_added_and_removed_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "ah.csv"
            base_path = notion_cli._ah_baseline_path(csv_path)
            notion_cli._write_csv(csv_path, [{"id": "SN-1", "name": "x", "status": "", "priority": "", "ah": "", "mr": "", "sort_date": "", "notion_url": ""}, {"id": "SN-3", "name": "x", "status": "", "priority": "", "ah": "", "mr": "", "sort_date": "", "notion_url": ""}], notion_cli.AH_WEEK_CSV_COLUMNS)
            notion_cli._write_csv(base_path, [{"id": "SN-1", "name": "x", "status": "", "priority": "", "ah": "", "mr": "", "sort_date": "", "notion_url": "", "project": "p"}, {"id": "SN-2", "name": "x", "status": "", "priority": "", "ah": "", "mr": "", "sort_date": "", "notion_url": "", "project": "p"}], notion_cli.AH_WEEK_CSV_COLUMNS + ["project"])

            self.assertEqual(notion_cli._ah_week_added_ids(csv_path, base_path), ["SN-3"])
            self.assertEqual(notion_cli._ah_week_removed_ids(csv_path, base_path), ["SN-2"])

    def test_read_csv_rows_skips_missing_and_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ah.csv"
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=notion_cli.AH_WEEK_CSV_COLUMNS)
                writer.writeheader()
                writer.writerow({"id": "SN-1", "name": "a", "status": "", "priority": "", "ah": "", "mr": "", "sort_date": "", "notion_url": ""})
                writer.writerow({"id": "SN-1", "name": "dup", "status": "", "priority": "", "ah": "", "mr": "", "sort_date": "", "notion_url": ""})
                writer.writerow({"id": "", "name": "no-id", "status": "", "priority": "", "ah": "", "mr": "", "sort_date": "", "notion_url": ""})

            rows = notion_cli._read_csv_rows(path)

        self.assertEqual([r["id"] for r in rows], ["SN-1"])
        self.assertEqual(rows[0]["name"], "a")

    def test_write_and_read_round_trip_preserves_commas_and_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ah.csv"
            notion_cli._write_csv(path, [{"id": "SN-1", "name": "fix: a, b \"quoted\"", "status": "Done", "priority": "High", "ah": "1.5", "mr": "", "sort_date": "2026-09-14", "notion_url": "u"}], notion_cli.AH_WEEK_CSV_COLUMNS)

            rows = notion_cli._read_csv_rows(path)

        self.assertEqual(rows[0]["name"], 'fix: a, b "quoted"')
        self.assertEqual(rows[0]["ah"], "1.5")

    def test_apply_patches_fields_and_refreshes_baseline_on_success(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "data-platform",
            "projects": {"data-platform": {"database_id": "tickets-db", "ticket_status_type": "select", "status_name_overrides": {"In progress": "In Progress"}}},
        })
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "ah.csv"
            base_path = notion_cli._ah_baseline_path(csv_path)
            base = {"id": "SN-1", "name": "x", "status": "In progress", "priority": "High", "ah": "", "mr": "", "sort_date": "2026-09-14", "notion_url": "u", "project": "data-platform"}
            edited = dict(base)
            edited["status"] = "Done"
            edited["ah"] = "2.0"
            notion_cli._write_csv(csv_path, [edited], notion_cli.AH_WEEK_CSV_COLUMNS)
            notion_cli._write_csv(base_path, [base], notion_cli.AH_WEEK_CSV_COLUMNS + ["project"])

            with (
                patch.object(notion_cli, "get_config", return_value=config),
                patch.object(notion_cli, "_resolve_page", return_value={"id": "uuid-1"}),
                patch.object(notion_cli, "_patch", return_value={}) as patch_page,
                redirect_stdout(io.StringIO()),
            ):
                notion_cli.ah_week(apply=True, out=str(csv_path))

            patch_page.assert_called_once_with(
                "/pages/uuid-1",
                {"properties": {"Status": {"select": {"name": "Done"}}, "AH": {"number": 2.0}}},
            )
            # Baseline refreshed to equal the edited CSV.
            self.assertEqual(notion_cli._ah_week_changes(csv_path, base_path), {})

    def test_apply_failure_does_not_refresh_baseline(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "data-platform",
            "projects": {"data-platform": {"database_id": "tickets-db"}},
        })
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "ah.csv"
            base_path = notion_cli._ah_baseline_path(csv_path)
            base = {"id": "SN-1", "name": "x", "status": "Done", "priority": "", "ah": "", "mr": "", "sort_date": "2026-09-14", "notion_url": "u", "project": "data-platform"}
            edited = dict(base)
            edited["priority"] = "Bogus"
            notion_cli._write_csv(csv_path, [edited], notion_cli.AH_WEEK_CSV_COLUMNS)
            notion_cli._write_csv(base_path, [base], notion_cli.AH_WEEK_CSV_COLUMNS + ["project"])

            with (
                patch.object(notion_cli, "get_config", return_value=config),
                patch.object(notion_cli, "_resolve_page", return_value={"id": "uuid-1"}),
                patch.object(notion_cli, "_patch") as patch_page,
                redirect_stdout(io.StringIO()),
                self.assertRaises(typer.Exit),
            ):
                notion_cli.ah_week(apply=True, out=str(csv_path))

            patch_page.assert_not_called()
            # Baseline untouched, so the diff survives for a retry.
            self.assertEqual(
                notion_cli._ah_week_changes(csv_path, base_path),
                {"SN-1": {"priority": ("", "Bogus")}},
            )

    def test_apply_mr_only_change_is_local_only(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "data-platform",
            "projects": {"data-platform": {"database_id": "tickets-db"}},
        })
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "ah.csv"
            base_path = notion_cli._ah_baseline_path(csv_path)
            base = {"id": "SN-1", "name": "x", "status": "Done", "priority": "High", "ah": "", "mr": "", "sort_date": "2026-09-14", "notion_url": "u", "project": "data-platform"}
            edited = dict(base)
            edited["mr"] = "https://git/mrs/1"
            notion_cli._write_csv(csv_path, [edited], notion_cli.AH_WEEK_CSV_COLUMNS)
            notion_cli._write_csv(base_path, [base], notion_cli.AH_WEEK_CSV_COLUMNS + ["project"])

            with (
                patch.object(notion_cli, "get_config", return_value=config),
                patch.object(notion_cli, "_resolve_page") as resolve_page,
                patch.object(notion_cli, "_patch") as patch_page,
                redirect_stdout(out),
            ):
                notion_cli.ah_week(apply=True, out=str(csv_path))

            resolve_page.assert_not_called()
            patch_page.assert_not_called()
            self.assertIn("local-only 1", out.getvalue())
            self.assertIn("kept in CSV/baseline only", out.getvalue())


class NotionCliReportTests(unittest.TestCase):
    def test_filter_uses_project_status_type_and_name_override(self) -> None:
        config = notion_cli.Config.model_validate({})
        proj = notion_cli.ProjectConfig.model_validate({
            "database_id": "tickets-db",
            "ticket_status_type": "select",
            "status_name_overrides": {"In progress": "In Progress"},
        })

        body = notion_cli._build_filter_body(config, status="In progress", proj=proj)

        self.assertEqual(
            body["filter"],
            {"property": "Status", "select": {"equals": "In Progress"}},
        )

    def test_report_groups_and_filters_by_due_date(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbook-global",
            "projects": {
                "genbook-global": {
                    "database_id": "tickets-db",
                    "date_property_type": "created_time",
                }
            },
            "users": {"cle": "creator-user-id"},
        })
        page = {
            "id": "ticket-page",
            "url": "https://notion.so/ticket-page",
            "properties": {
                "Name": {"title": [{"plain_text": "Backfill AH by day"}]},
                "Assignee": {"people": [{"name": "cle"}]},
                "AH": {"number": 6},
                "Due Date": {"type": "date", "date": {"start": "2026-07-01"}},
                "Sort Date": {
                    "formula": {
                        "type": "date",
                        "date": {"start": "2026-06-25"},
                    }
                },
                "Created time": {"type": "created_time", "created_time": "2026-06-25T03:00:00Z"},
            },
        }
        stdout = io.StringIO()

        with (
            patch.object(notion_cli, "get_config", return_value=config),
            patch.object(notion_cli, "_query_database", return_value=[page]) as query_database,
            redirect_stdout(stdout),
        ):
            notion_cli.report(
                period=notion_cli.Period.WEEKLY,
                assignee="cle",
                since=date(2026, 7, 1),
                project="genbook-global",
            )

        query_database.assert_called_once_with(
            "tickets-db",
            {
                "page_size": 100,
                "sorts": [{"property": "Due Date", "direction": "descending"}],
                "filter": {
                    "and": [
                        {"property": "Assignee", "people": {"contains": "creator-user-id"}},
                        {"property": "Due Date", "date": {"on_or_after": "2026-07-01"}},
                    ]
                },
            },
        )
        output = stdout.getvalue()
        self.assertIn("AH Report (weekly)", output)
        self.assertIn("2026-W27", output)
        self.assertNotIn("2026-W26", output)

    def test_report_skips_tickets_without_due_date(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbook-global",
            "projects": {"genbook-global": {"database_id": "tickets-db"}},
        })
        page = {
            "id": "ticket-page",
            "url": "https://notion.so/ticket-page",
            "properties": {
                "Name": {"title": [{"plain_text": "Missing due date"}]},
                "AH": {"number": 6},
                "Sort Date": {
                    "formula": {
                        "type": "date",
                        "date": {"start": "2026-06-25"},
                    }
                },
            },
        }
        stdout = io.StringIO()

        with (
            patch.object(notion_cli, "get_config", return_value=config),
            patch.object(notion_cli, "_query_database", return_value=[page]),
            redirect_stdout(stdout),
        ):
            notion_cli.report(period=notion_cli.Period.WEEKLY, project="genbook-global")

        self.assertEqual(stdout.getvalue().strip(), "No tickets with AH found.")


if __name__ == "__main__":
    unittest.main()
