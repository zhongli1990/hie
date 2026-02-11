import { NextRequest, NextResponse } from "next/server";
import { readdir, readFile, stat } from "fs/promises";
import { join } from "path";
import { existsSync } from "fs";
import archiver from "archiver";
import { Readable } from "stream";

const PROJECT_FILES_BASE = process.env.PROJECT_FILES_PATH || "/app/data/project-files";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const workspace_id = searchParams.get("workspace_id");
    const project_id = searchParams.get("project_id");

    if (!workspace_id || !project_id) {
      return NextResponse.json(
        { error: "workspace_id and project_id are required" },
        { status: 400 }
      );
    }

    const projectDir = join(PROJECT_FILES_BASE, workspace_id, project_id);

    if (!existsSync(projectDir)) {
      return NextResponse.json(
        { error: "Project directory not found" },
        { status: 404 }
      );
    }

    // Create a zip archive
    const archive = archiver("zip", { zlib: { level: 9 } });

    // Convert archive stream to web stream
    const stream = Readable.toWeb(archive) as ReadableStream;

    // Add all files from the project directory
    const files = await readdir(projectDir);
    for (const filename of files) {
      const filepath = join(projectDir, filename);
      const fileStat = await stat(filepath);

      if (fileStat.isFile()) {
        const content = await readFile(filepath);
        archive.append(content, { name: filename });
      }
    }

    // Finalize the archive
    archive.finalize();

    return new NextResponse(stream, {
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": `attachment; filename="project-${project_id}-files.zip"`,
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
