"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface WarnFormProps {
  moderatorId?: string;
  moderatorName?: string;
}

export function WarnForm({ moderatorId, moderatorName }: WarnFormProps) {
  const [userId, setUserId] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    // Validation
    if (!userId.trim()) {
      setError("L'ID de l'utilisateur est requis");
      setLoading(false);
      return;
    }

    if (!reason.trim()) {
      setError("La raison est requise");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch("/api/moderation/warn", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: parseInt(userId.trim()),
          reason: reason.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        // Gérer les erreurs
        const errorMessage = data.detail || data.message || "Une erreur est survenue";
        setError(errorMessage);
        return;
      }

      // Succès
      setSuccess(`Avertissement donné avec succès ! L'utilisateur a maintenant ${data.warn_count || 0} avertissement(s).`);
      setUserId("");
      setReason("");
    } catch (err) {
      setError("Erreur de connexion. Vérifiez que le bot Hermes est en ligne.");
      console.error("Erreur:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="userId">ID Discord de l'utilisateur</Label>
        <Input
          id="userId"
          type="text"
          placeholder="123456789012345678"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          disabled={loading}
          required
        />
        <p className="text-sm text-muted-foreground">
          L'ID Discord de l'utilisateur à avertir (activez le mode développeur sur Discord pour le copier)
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="reason">Raison de l'avertissement</Label>
        <Input
          id="reason"
          type="text"
          placeholder="Comportement inapproprié"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          disabled={loading}
          required
        />
      </div>

      {error && (
        <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-red-800 dark:text-red-200">
                {error}
              </p>
            </div>
          </div>
        </div>
      )}

      {success && (
        <div className="rounded-md bg-green-50 dark:bg-green-900/20 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-green-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-green-800 dark:text-green-200">
                {success}
              </p>
            </div>
          </div>
        </div>
      )}

      <Button type="submit" disabled={loading} className="w-full">
        {loading ? "Envoi en cours..." : "Donner l'avertissement"}
      </Button>
    </form>
  );
}

