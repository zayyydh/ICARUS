"""
ICARUS GitHub Tool
===================
Creates repos, pushes files, lists repos — via voice command.

Requires: pip install PyGithub
Requires: GITHUB_TOKEN in .env with repo scope

Triggers:
  "push to github"        → GITHUB_PUSH
  "create repo my-proj"   → GITHUB_CREATE
  "list my repos"         → GITHUB_LIST
"""

import logging
from pathlib import Path

from app.tools.base import BaseTool, ToolResult
from app.config.settings import settings

logger = logging.getLogger(__name__)


class GitHubTool(BaseTool):

    @property
    def name(self) -> str:
        return "github"

    @property
    def description(self) -> str:
        return "Create GitHub repos, push code, and list repositories"

    @property
    def triggers(self) -> list[str]:
        return [
            "push", "github", "repo", "repository",
            "commit", "upload code", "publish project",
        ]

    async def execute(self, input: str, context: dict) -> ToolResult:
        """
        Route to the right GitHub action based on intent in context.
        context["intent"] tells us what to do.
        """
        intent = context.get("intent", "")
        params = context.get("params", {})

        if not settings.GITHUB_TOKEN:
            return ToolResult(
                success=False,
                output=None,
                message="GitHub token not configured. Add GITHUB_TOKEN to .env",
                tool_name=self.name,
            )

        try:
            from github import Github, GithubException
            client = Github(settings.GITHUB_TOKEN)
            user   = client.get_user()

            if "create" in intent:
                return await self._create_repo(user, params)
            elif "list" in intent:
                return await self._list_repos(user)
            else:
                return await self._push_files(user, params, context)

        except ImportError:
            return ToolResult(
                success=False,
                output=None,
                message="PyGithub not installed. Run: pip install PyGithub",
                tool_name=self.name,
            )
        except Exception as e:
            logger.error("GitHub tool error", extra={"error": str(e)})
            return ToolResult(
                success=False,
                output=None,
                message=f"GitHub error: {str(e)}",
                tool_name=self.name,
            )

    async def _create_repo(self, user, params: dict) -> ToolResult:
        """Create a new GitHub repository."""
        from github import GithubException

        name        = params.get("repo_name", "icarus-project")
        description = params.get("description", "Created by ICARUS")
        private     = params.get("private", False)

        # Clean repo name — no spaces, lowercase
        name = name.replace(" ", "-").lower()

        try:
            repo = user.create_repo(
                name=name,
                description=description,
                private=private,
                auto_init=True,
            )
            logger.info("Repo created", extra={"repo": repo.full_name})
            return ToolResult(
                success=True,
                output={
                    "url":     repo.html_url,
                    "name":    repo.full_name,
                    "private": repo.private,
                },
                message=f"Repository '{name}' created at {repo.html_url}",
                tool_name=self.name,
            )
        except GithubException as e:
            if e.status == 422:
                return ToolResult(
                    success=False,
                    output=None,
                    message=f"Repository '{name}' already exists",
                    tool_name=self.name,
                )
            raise

    async def _list_repos(self, user) -> ToolResult:
        """List the user's most recent repos."""
        repos = list(user.get_repos(sort="updated"))[:10]
        repo_list = [
            {
                "name":    r.full_name,
                "url":     r.html_url,
                "private": r.private,
                "stars":   r.stargazers_count,
            }
            for r in repos
        ]
        return ToolResult(
            success=True,
            output=repo_list,
            message=f"Found {len(repo_list)} repositories",
            tool_name=self.name,
        )

    async def _push_files(self, user, params: dict, context: dict) -> ToolResult:
        """Push files to an existing or new repo."""
        from github import GithubException

        repo_name = params.get("repo_name", "")
        files     = context.get("files", {})   # {path: content} dict

        if not repo_name:
            return ToolResult(
                success=False,
                output=None,
                message="Repo name required. Say: 'push to github repo my-project'",
                tool_name=self.name,
            )

        if not files:
            # If no files provided, just confirm the repo exists
            try:
                repo = user.get_repo(repo_name)
                return ToolResult(
                    success=True,
                    output={"url": repo.html_url},
                    message=f"Connected to {repo.html_url}",
                    tool_name=self.name,
                )
            except GithubException:
                return ToolResult(
                    success=False,
                    output=None,
                    message=f"Repo '{repo_name}' not found. Create it first.",
                    tool_name=self.name,
                )

        # Push files
        try:
            repo    = user.get_repo(repo_name)
            pushed  = []

            for filepath, content in files.items():
                try:
                    existing = repo.get_contents(filepath)
                    repo.update_file(
                        path=filepath,
                        message=f"Update {filepath} via ICARUS",
                        content=content,
                        sha=existing.sha,
                    )
                    pushed.append(f"Updated: {filepath}")
                except GithubException:
                    repo.create_file(
                        path=filepath,
                        message=f"Add {filepath} via ICARUS",
                        content=content,
                    )
                    pushed.append(f"Created: {filepath}")

            return ToolResult(
                success=True,
                output={"pushed": pushed, "url": repo.html_url},
                message=f"Pushed {len(pushed)} files to {repo.html_url}",
                tool_name=self.name,
            )

        except Exception as e:
            raise

    async def generate_readme(self, project_name: str, description: str) -> str:
        """Ask LLM to generate a README for a project before pushing."""
        from app.llm.manager import llm
        prompt = (
            f"Write a clean GitHub README.md for:\n"
            f"Project: {project_name}\n"
            f"Description: {description}\n"
            f"Include: title, description, features, installation, usage, tech stack.\n"
            f"Use proper Markdown. Be concise."
        )
        return await llm.quick(prompt)