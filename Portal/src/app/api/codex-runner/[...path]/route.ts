/**
 * OpenLI HIE - Codex Runner Proxy
 * Forwards requests to the hie-codex-runner service (OpenAI Codex SDK).
 * Same API contract as agent-runner: /threads, /runs, /runs/:id/events
 */

import { NextRequest, NextResponse } from "next/server";

const CODEX_RUNNER_URL = process.env.CODEX_RUNNER_URL || "http://hie-codex-runner:8081";

function getAuthHeader(request: NextRequest): Record<string, string> {
  const authHeader = request.headers.get("Authorization");
  if (authHeader) {
    return { Authorization: authHeader };
  }
  return {};
}

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${CODEX_RUNNER_URL}/${path}${searchParams ? `?${searchParams}` : ""}`;

  try {
    const res = await fetch(url, {
      method: "GET",
      headers: {
        ...getAuthHeader(request),
      },
      cache: "no-store",
    });

    // SSE streaming for /runs/{id}/events
    if (res.headers.get("content-type")?.includes("text/event-stream")) {
      return new NextResponse(res.body, {
        status: res.status,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache, no-transform",
          "Connection": "keep-alive",
          "X-Accel-Buffering": "no",
        },
      });
    }

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Codex Runner proxy error:", error);
    return NextResponse.json({ detail: "Codex Runner service unavailable" }, { status: 502 });
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");

  try {
    const body = await request.json();
    const res = await fetch(`${CODEX_RUNNER_URL}/${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeader(request),
      },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Codex Runner proxy error:", error);
    return NextResponse.json({ detail: "Codex Runner service unavailable" }, { status: 502 });
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");

  try {
    const body = await request.json();
    const res = await fetch(`${CODEX_RUNNER_URL}/${path}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeader(request),
      },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Codex Runner proxy error:", error);
    return NextResponse.json({ detail: "Codex Runner service unavailable" }, { status: 502 });
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join("/");

  try {
    const res = await fetch(`${CODEX_RUNNER_URL}/${path}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeader(request),
      },
    });

    if (res.status === 204) {
      return new NextResponse(null, { status: 204 });
    }

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Codex Runner proxy error:", error);
    return NextResponse.json({ detail: "Codex Runner service unavailable" }, { status: 502 });
  }
}
