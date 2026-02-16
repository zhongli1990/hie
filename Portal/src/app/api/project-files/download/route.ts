import { NextRequest, NextResponse } from "next/server";
import { readdir, readFile, stat } from "fs/promises";
import { join, resolve } from "path";
import { existsSync } from "fs";
import archiver from "archiver";
import { Readable } from "stream";

const WORKSPACES_ROOT = process.env.WORKSPACES_ROOT || "/workspaces";

function validatePath(base: string, target: string): string {
  const resolvedBase = resolve(base);
  const resolvedTarget = resolve(target);
  if (!resolvedTarget.startsWith(resolvedBase)) {
    throw new Error("Path traversal detected");
  }
  return resolvedTarget;
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const workspace_id = searchParams.get("workspace_id");
    const project_id = searchParams.get("project_id");
    const filePath = searchParams.get("path");

    if (!workspace_id) {
      return NextResponse.json(
        { error: "workspace_id is required" },
        { status: 400 }
      );
    }

    // Build workspace directory path
    const wsDir = project_id
      ? join(WORKSPACES_ROOT, workspace_id, project_id)
      : join(WORKSPACES_ROOT, workspace_id);

    const targetDir = filePath
      ? validatePath(WORKSPACES_ROOT, join(wsDir, filePath))
      : validatePath(WORKSPACES_ROOT, wsDir);

    if (!existsSync(targetDir)) {
      return NextResponse.json(
        { error: "Directory not found" },
        { status: 404 }
      );
    }

    // Check if it's a single file download
    const fileStat = await stat(targetDir);
    if (fileStat.isFile()) {
      const content = await readFile(targetDir);
      const filename = targetDir.split("/").pop() || "file";
      return new NextResponse(content, {
        headers: {
          "Content-Type": "application/octet-stream",
          "Content-Disposition": `attachment; filename="${filename}"`,
        },
      });
    }

    // Directory download as ZIP
    const archive = archiver("zip", { zlib: { level: 9 } });
    const stream = Readable.toWeb(archive) as ReadableStream;

    // Recursively add all files
    archive.directory(targetDir, false);
    archive.finalize();

    const zipName = project_id
      ? `${project_id}-files.zip`
      : `${workspace_id}-files.zip`;

    return new NextResponse(stream, {
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": `attachment; filename="${zipName}"`,
      },
    });
  } catch (error) {
    console.error("Download error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Download failed" },
      { status: 500 }
    );
  }
}
