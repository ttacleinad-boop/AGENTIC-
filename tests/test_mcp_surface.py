from __future__ import annotations

import unittest

from mcp import Client

from agentic_core.mcp_server import mcp


class McpSurfaceTests(unittest.IsolatedAsyncioTestCase):
    async def test_status_is_available_through_mcp(self) -> None:
        async with Client(mcp) as client:
            result = await client.call_tool("core_status", {})
        self.assertEqual(result.structured_content["status"], "ready")

    async def test_golden_evaluation_is_available_through_mcp(self) -> None:
        async with Client(mcp) as client:
            result = await client.call_tool("core_evaluate", {})
        self.assertEqual(result.structured_content["overall"], "PASS")

    async def test_approval_resume_lifecycle_is_available_through_mcp(self) -> None:
        async with Client(mcp) as client:
            result = await client.call_tool("core_demo", {"input_text": "write:mcp approval"})
        self.assertEqual(result.structured_content["resumed"]["status"], "succeeded")


if __name__ == "__main__":
    unittest.main()
