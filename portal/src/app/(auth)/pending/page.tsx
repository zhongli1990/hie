"use client";

import Link from "next/link";
import { Clock, Mail, ArrowLeft } from "lucide-react";

export default function PendingPage() {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-xl text-center">
      <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-amber-100">
        <Clock className="h-8 w-8 text-amber-600" />
      </div>

      <h2 className="text-xl font-semibold text-gray-900">Account Pending Approval</h2>
      
      <p className="mt-4 text-sm text-gray-600">
        Your registration has been submitted successfully. An administrator will review your request shortly.
      </p>

      <div className="mt-6 rounded-lg bg-blue-50 border border-blue-200 p-4">
        <div className="flex items-start gap-3">
          <Mail className="h-5 w-5 text-blue-600 mt-0.5" />
          <div className="text-left">
            <p className="text-sm font-medium text-blue-900">What happens next?</p>
            <ul className="mt-2 text-sm text-blue-700 space-y-1">
              <li>• An admin will review your registration</li>
              <li>• You&apos;ll receive an email when approved</li>
              <li>• Once approved, you can sign in normally</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="mt-8">
        <Link
          href="/login"
          className="inline-flex items-center gap-2 text-sm font-medium text-nhs-blue hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to login
        </Link>
      </div>
    </div>
  );
}
