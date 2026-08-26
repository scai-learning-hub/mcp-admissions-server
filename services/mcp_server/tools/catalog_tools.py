"""Catalog tools — search_courses, get_course."""

from __future__ import annotations

from packages.contracts.tool_inputs import CatalogGetCourseInput, CatalogSearchCoursesInput
from packages.contracts.tool_outputs import CatalogGetCourseOutput, CatalogSearchCoursesOutput
from services.mcp_server.context import RequestContext
from services.mcp_server.domain.catalog import CatalogService
from services.mcp_server.tools._runner import run_tool, sync_handler


async def catalog_search_courses(ctx: RequestContext, args: dict) -> dict:
    from packages.contracts.domain import CourseSummary

    async def handler(validated, sess):
        svc = CatalogService(sess)
        courses = svc.search_courses(
            validated.query,
            mode=validated.mode,
            level=validated.level,
            limit=validated.limit,
        )
        return CatalogSearchCoursesOutput(
            courses=courses,
            total=len(courses),
        )

    return await run_tool(ctx, "catalog.search_courses", CatalogSearchCoursesInput, args, handler)


async def catalog_get_course(ctx: RequestContext, args: dict) -> dict:
    async def handler(validated, sess):
        svc = CatalogService(sess)
        course = svc.get_course(validated.slug_or_id)
        if course is None:
            from packages.contracts.error_codes import ErrorCode

            return (ErrorCode.COURSE_NOT_FOUND, "Course not found.")
        return CatalogGetCourseOutput(course=course)

    return await run_tool(ctx, "catalog.get_course", CatalogGetCourseInput, args, handler)


__all__ = ["catalog_get_course", "catalog_search_courses"]