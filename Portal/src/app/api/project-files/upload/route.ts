import { NextRequest, NextResponse } from "next/server";
import { writeFile, mkdir } from "fs/promises";
import { join, resolve } from "path";
import { existsSync } from "fs";

const WORKSPACES_ROOT = process.env.WORKSPACES_ROOT || "/workspaces";

function validatePath(base: string, target: string): string {
  const resolvedBase = resolve(base);
  const resolvedTarget = resolve(target);
  if (!resolvedTarget.startsWith(resolvedBase)) {
    throw new Error("Path traversal detected");
  }
  return resolvedTarget;
}

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const workspace_id = formData.get("workspace_id") as string;
    const project_id = formData.get("project_id") as string;
    const targetPath = (formData.get("path") as string) || "/";
    const files = formData.getAll("files") as File[];

    if (!workspace_id) {
      return NextResponse.json(
        { error: "workspace_id is required" },
        { status: 400 }
      );
    }

    if (files.length === 0) {
      return NextResponse.json({ error: "No files provided" }, { status: 400 });
    }

    // Build workspace directory path
    const wsDir = project_id
      ? join(WORKSPACES_ROOT, workspace_id, project_id)
      : join(WORKSPACES_ROOT, workspace_id);

    const uploadDir = validatePath(WORKSPACES_ROOT, join(wsDir, targetPath));

    if (!existsSync(uploadDir)) {
      await mkdir(uploadDir, { recursive: true });
    }

    const uploadedFiles: string[] = [];

    for (const file of files) {
      const bytes = await file.arrayBuffer();
      const buffer = Buffer.from(bytes);

      // Preserve original filename but sanitize path components
      const safeName = file.name.split("/").pop()?.replace(/[<>:"|?*]/g, "_") || "unnamed";
      const filepath = validatePath(WORKSPACES_ROOT, join(uploadDir, safeName));

      // Ensure parent directory exists (for nested paths from webkitdirectory)
      const parentDir = filepath.substring(0, filepath.lastIndexOf("/"));
      if (!existsSync(parentDir)) {
        await mkdir(parentDir, { recursive: true });
      }

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
