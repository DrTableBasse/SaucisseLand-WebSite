import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";

// URL de l'API Hermes (à configurer dans les variables d'environnement)
const HERMES_API_URL = process.env.HERMES_API_URL || "http://localhost:8001";
const HERMES_API_TOKEN = process.env.HERMES_API_TOKEN;
const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    // Vérifier l'authentification
    const session = await auth();
    if (!session || !session.user) {
      return NextResponse.json(
        { detail: "Non authentifié" },
        { status: 401 }
      );
    }

    // Vérifier que le token API est configuré
    if (!HERMES_API_TOKEN) {
      console.error("HERMES_API_TOKEN non configuré dans les variables d'environnement");
      return NextResponse.json(
        { detail: "Configuration serveur manquante" },
        { status: 500 }
      );
    }

    // Récupérer l'utilisateur depuis le backend pour obtenir son discord_id
    const cookieHeader = request.headers.get("cookie") || "";
    const sessionCookie = cookieHeader.split("; ").find(c => c.startsWith("session="));
    
    let discordId: string | null = null;
    let moderatorName: string = session.user.name || "Modérateur";

    if (sessionCookie) {
      try {
        const userResponse = await fetch(`${BACKEND_API_URL}/api/auth/me`, {
          headers: {
            Cookie: sessionCookie,
          },
        });

        if (userResponse.ok) {
          const user = await userResponse.json();
          discordId = user.discord_id;
          moderatorName = user.username || moderatorName;
        }
      } catch (error) {
        console.error("Erreur lors de la récupération de l'utilisateur:", error);
      }
    }

    if (!discordId) {
      return NextResponse.json(
        { detail: "Impossible de récupérer l'ID Discord de l'utilisateur" },
        { status: 401 }
      );
    }

    // Récupérer les données de la requête
    const body = await request.json();
    const { user_id, reason } = body;

    // Validation
    if (!user_id) {
      return NextResponse.json(
        { detail: "user_id est requis" },
        { status: 400 }
      );
    }

    // Appeler l'API Hermes
    const response = await fetch(`${HERMES_API_URL}/warn`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${HERMES_API_TOKEN}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: parseInt(user_id),
        reason: reason || "Aucune raison spécifiée",
        moderator_id: parseInt(discordId),
        moderator_name: moderatorName,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      // Retourner l'erreur de l'API Hermes
      return NextResponse.json(
        { detail: data.detail || "Erreur lors de l'appel à l'API Hermes" },
        { status: response.status }
      );
    }

    // Succès
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error("Erreur dans /api/moderation/warn:", error);
    return NextResponse.json(
      { detail: "Erreur interne du serveur" },
      { status: 500 }
    );
  }
}

