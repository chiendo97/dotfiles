from __future__ import annotations

import io
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
            patch.object(notion_cli, "_find_epic_id", return_value=None),
            patch.object(notion_cli, "_patch") as patch_page,
            redirect_stderr(io.StringIO()),
            self.assertRaises(typer.Exit),
        ):
            notion_cli.update(page_id="ticket-page", epic="Missing Epic", project="genbook-global")

        patch_page.assert_not_called()


class NotionCliReportTests(unittest.TestCase):
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
