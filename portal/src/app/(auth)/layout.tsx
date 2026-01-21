export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-nhs-blue to-nhs-dark-blue p-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white">HIE</h1>
          <p className="mt-1 text-sm text-blue-100">Healthcare Integration Engine</p>
        </div>
        {children}
      </div>
    </div>
  );
}
