from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from unittest.mock import patch

import typer

import notion_cli


class NotionCliCreateTests(unittest.TestCase):
    def test_project_config_keeps_sprint_fields(self) -> None:
        proj = notion_cli.ProjectConfig.model_validate({
            "database_id": "tickets-db",
            "sprints_data_source_id": "sprints-ds",
            "prop_sprint": "Sprint",
            "prop_sprint_date": "Start Date",
        })

        self.assertEqual(proj.sprints_data_source_id, "sprints-ds")
        self.assertEqual(proj.prop_sprint, "Sprint")
        self.assertEqual(proj.prop_sprint_date, "Start Date")

    def test_config_keeps_default_creator_alias(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbooks",
            "default_creator_alias": "owner",
        })

        self.assertEqual(config.default_creator_alias, "owner")

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

    def test_create_defaults_to_creator_and_current_sprint(self) -> None:
        config = notion_cli.Config.model_validate({
            "default_project": "genbooks",
            "default_creator_alias": "owner",
            "projects": {
                "genbooks": {
                    "database_id": "tickets-db",
                    "sprints_data_source_id": "sprints-ds",
                    "prop_sprint": "Sprint",
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
            patch.object(notion_cli, "_find_current_sprint_id", return_value="sprint-page"),
            patch.object(notion_cli, "_post", return_value=created_page) as post,
            redirect_stdout(io.StringIO()),
        ):
            notion_cli.create(title="Fix auth bug")

        post.assert_called_once()
        _, payload = post.call_args.args
        self.assertEqual(payload["parent"], {"database_id": "tickets-db"})
        self.assertEqual(payload["properties"]["Assignee"], {"people": [{"id": "creator-user-id"}]})
        self.assertEqual(payload["properties"]["Sprint"], {"relation": [{"id": "sprint-page"}]})

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
            notion_cli.create(title="Fix auth bug")

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
            notion_cli.create(title="Fix auth bug")

        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
