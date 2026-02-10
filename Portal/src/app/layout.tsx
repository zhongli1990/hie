/**
 * OpenLI HIE - Healthcare Integration Engine
 * Copyright (c) 2026 Lightweight Integration Ltd
 * 
 * This file is part of OpenLI HIE.
 * Licensed under AGPL-3.0 (community) or Commercial license.
 * See LICENSE file for details.
 * 
 * Contact: zhong@li-ai.co.uk
 */

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "OpenLI HIE | Healthcare Integration Engine",
  description: "OpenLI HIE - Enterprise-grade healthcare integration platform for NHS trusts and healthcare organizations. Configuration-driven HL7, FHIR, and multi-protocol messaging.",
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
  },
  applicationName: "OpenLI HIE",
  keywords: ["Healthcare", "Integration", "HL7", "FHIR", "NHS", "HIE", "Enterprise", "OpenLI"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} min-h-screen bg-gray-50 text-gray-900 dark:bg-zinc-900 dark:text-zinc-100`}>{children}</body>
    </html>
  );
}
