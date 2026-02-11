import { NextRequest, NextResponse } from "next/server";

const MANAGER_API_URL = process.env.MANAGER_API_URL || "http://hie-manager:8081";

function getAuthHeader(request: NextRequest): Record<string, string> {
  const authHeader = request.headers.get("Authorization");
  if (authHeader) {
    return { Authorization: authHeader };
  }
  // Also check for cookie-based auth
  const cookie = request.headers.get("Cookie");
  if (cookie) {
    return { Cookie: cookie };
  }
  return {};
}

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path ? params.path.join("/") : "";
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${MANAGER_API_URL}/api/genai-sessions${path ? `/${path}` : ""}${searchParams ? `?${searchParams}` : ""}`;

  try {
    const res = await fetch(url, {
      method: "GET",
      headers: {
        ...getAuthHeader(request),
      },
      cache: "no-store",
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("GenAI Sessions API proxy error:", error);
    return NextResponse.json({ detail: "Manager API service unavailable" }, { status: 502 });
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path ? params.path.join("/") : "";

  try {
    const body = await request.json();
    const res = await fetch(`${MANAGER_API_URL}/api/genai-sessions${path ? `/${path}` : ""}`, {
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
    console.error("GenAI Sessions API proxy error:", error);
    return NextResponse.json({ detail: "Manager API service unavailable" }, { status: 502 });
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path ? params.path.join("/") : "";

  try {
    const body = await request.json();
    const res = await fetch(`${MANAGER_API_URL}/api/genai-sessions${path ? `/${path}` : ""}`, {
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
    console.error("GenAI Sessions API proxy error:", error);
    return NextResponse.json({ detail: "Manager API service unavailable" }, { status: 502 });
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path ? params.path.join("/") : "";

  try {
    const res = await fetch(`${MANAGER_API_URL}/api/genai-sessions${path ? `/${path}` : ""}`, {
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
    console.error("GenAI Sessions API proxy error:", error);
    return NextResponse.json({ detail: "Manager API service unavailable" }, { status: 502 });
  }
}
