import { NextRequest, NextResponse } from "next/server";
import { readdir, stat, readFile } from "fs/promises";
import { join, resolve, extname } from "path";
import { existsSync } from "fs";

const WORKSPACES_ROOT = process.env.WORKSPACES_ROOT || "/workspaces";

const VIEWABLE_EXTENSIONS = new Set([
  ".md", ".txt", ".json", ".yaml", ".yml", ".xml",
  ".py", ".js", ".ts", ".tsx", ".jsx", ".java",
  ".html", ".css", ".sql", ".sh", ".bash",
  ".csv", ".log", ".conf", ".ini", ".toml",
  ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
]);

const MAX_VIEW_SIZE = 1 * 1024 * 1024; // 1MB

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
    const relativePath = searchParams.get("path") || "/";
    const action = searchParams.get("action") || "list"; // list | view

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

    const targetPath = validatePath(WORKSPACES_ROOT, join(wsDir, relativePath));

    if (!existsSync(targetPath)) {
      // If workspace doesn't exist, return empty listing
      if (relativePath === "/" || relativePath === "") {
        return NextResponse.json({
          current_path: "/",
          parent_path: null,
          items: [],
        });
      }
      return NextResponse.json({ error: "Path not found" }, { status: 404 });
    }

    const fileStat = await stat(targetPath);

    // View file content
    if (action === "view" && fileStat.isFile()) {
      if (fileStat.size > MAX_VIEW_SIZE) {
        return NextResponse.json(
          { error: "File too large to view (max 1MB)" },
          { status: 413 }
        );
      }

      const ext = extname(targetPath).toLowerCase();
      const isViewable = VIEWABLE_EXTENSIONS.has(ext);

      if (!isViewable) {
        return NextResponse.json({
          name: targetPath.split("/").pop(),
          path: relativePath,
          size: fileStat.size,
          is_binary: true,
          content: null,
        });
      }

      const content = await readFile(targetPath, "utf-8");
      return NextResponse.json({
        name: targetPath.split("/").pop(),
        path: relativePath,
        size: fileStat.size,
        is_binary: false,
        content,
        modified_at: fileStat.mtime.toISOString(),
      });
    }

    // List directory
    if (!fileStat.isDirectory()) {
      return NextResponse.json(
        { error: "Path is not a directory" },
        { status: 400 }
      );
    }

    const entries = await readdir(targetPath);
    const items: {
      name: string;
      path: string;
      type: "file" | "directory";
      size: number | null;
      modified_at: string;
    }[] = [];

    for (const entry of entries) {
      // Skip hidden files/directories
      if (entry.startsWith(".")) continue;

      const entryPath = join(targetPath, entry);
      try {
        const entryStat = await stat(entryPath);
        const entryRelPath =
          relativePath === "/" ? `/${entry}` : `${relativePath}/${entry}`;

        items.push({
          name: entry,
          path: entryRelPath,
          type: entryStat.isDirectory() ? "directory" : "file",
          size: entryStat.isDirectory() ? null : entryStat.size,
          modified_at: entryStat.mtime.toISOString(),
        });
      } catch {
        // Skip entries we can't access
      }
    }

    // Sort: directories first, then alphabetical
    items.sort((a, b) => {
      if (a.type !== b.type) return a.type === "directory" ? -1 : 1;
      return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
    });

    // Calculate parent path
    let parentPath: string | null = null;
    if (relativePath !== "/" && relativePath !== "") {
      const parts = relativePath.split("/").filter(Boolean);
      parts.pop();
      parentPath = parts.length === 0 ? "/" : "/" + parts.join("/");
    }

    return NextResponse.json({
      current_path: relativePath === "" ? "/" : relativePath,
      parent_path: parentPath,
      items,
    });
  } catch (error) {
    console.error("File list error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to list files" },
      { status: 500 }
    );
  }
}
