import { NextRequest, NextResponse } from "next/server";
import { writeFile, mkdir } from "fs/promises";
import { join } from "path";
import { existsSync } from "fs";

const PROJECT_FILES_BASE = process.env.PROJECT_FILES_PATH || "/app/data/project-files";

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const workspace_id = formData.get("workspace_id") as string;
    const project_id = formData.get("project_id") as string;
    const files = formData.getAll("files") as File[];

    if (!workspace_id || !project_id) {
      return NextResponse.json(
        { error: "workspace_id and project_id are required" },
        { status: 400 }
      );
    }

    if (files.length === 0) {
      return NextResponse.json({ error: "No files provided" }, { status: 400 });
    }

    // Create project directory if it doesn't exist
    const projectDir = join(PROJECT_FILES_BASE, workspace_id, project_id);
    if (!existsSync(projectDir)) {
      await mkdir(projectDir, { recursive: true });
    }

    const uploadedFiles: string[] = [];

    for (const file of files) {
      const bytes = await file.arrayBuffer();
      const buffer = Buffer.from(bytes);

      // Sanitize filename to prevent directory traversal
      const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
      const filepath = join(projectDir, safeName);

      await writeFile(filepath, buffer);
      uploadedFiles.push(safeName);
    }

    return NextResponse.json({
      success: true,
      uploaded: uploadedFiles.length,
      files: uploadedFiles,
    });
  } catch (error) {
    console.error("Upload error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Upload failed" },
      { status: 500 }
    );
  }
}
