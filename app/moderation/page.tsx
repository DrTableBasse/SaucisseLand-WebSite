import { Metadata } from "next";
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { WarnForm } from "@/components/moderation/warn-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { MainNav } from "@/components/dashboard/main-nav";
import { SignIn } from "@/components/dashboard/signIn";
import { ModeToggle } from "@/components/ui/ModeToggle";
import { Search } from "@/components/dashboard/search";

export const metadata: Metadata = {
  title: "Modération - Hermes Bot",
  description: "Gestion des sanctions Discord via Hermes Bot",
};

export default async function ModerationPage() {
  const session = await auth();
  
  if (!session) {
    return (
      <>
        <div className="border-b">
          <div className="flex h-16 items-center px-4">
            <MainNav className="mx-6" />
            <div className="ml-auto flex items-center space-x-4">
              <Search />
              <ModeToggle />
              <SignIn />
            </div>
          </div>
        </div>
        <div className="hidden md:grid place-items-center overflow-hidden" style={{ height: 'calc(100vh - 66px)' }}>
          <Card>
            <CardHeader>
              <CardTitle>⚠️ Accès restreint</CardTitle>
              <CardDescription>
                Vous devez être connecté pour accéder à la page de modération.
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="hidden flex-col md:flex">
        <div className="border-b">
          <div className="flex h-16 items-center px-4">
            <MainNav className="mx-6" />
            <div className="ml-auto flex items-center space-x-4">
              <Search />
              <ModeToggle />
              <SignIn />
            </div>
          </div>
        </div>
        <div className="flex-1 space-y-4 p-8 pt-6">
          <div className="flex items-center justify-between space-y-2">
            <h2 className="text-3xl font-bold tracking-tight">Modération Discord</h2>
          </div>
          <Card>
            <CardHeader>
              <CardTitle>⚠️ Donner un avertissement</CardTitle>
              <CardDescription>
                Utilisez ce formulaire pour donner un avertissement à un utilisateur Discord via le bot Hermes.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <WarnForm />
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}

