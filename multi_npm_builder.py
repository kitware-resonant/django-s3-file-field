from __future__ import annotations

from typing import TypedDict

from hatch_jupyter_builder import npm_builder


class BuildKwargs(TypedDict):
    build_cmd: str
    path: str
    source_dir: str
    build_dir: str


def multi_npm_builder(
    target_name: str,
    version: str,
    *,
    projects: list[BuildKwargs],
) -> None:
    for project in projects:
        # TODO: allow multiple source_dir for a build, so the "widget" will be rebuilt when
        #  the "javascript-client" changes
        npm_builder(
            target_name,
            version,
            build_cmd=project["build_cmd"],
            path=project["path"],
            source_dir=project["source_dir"],
            build_dir=project["build_dir"],
        )
