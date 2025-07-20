import { useEffect } from "react";
import { useNavigate } from "react-router";
import type { Route } from "./+types/home";
import { Loading } from "~/components/Loading";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "BD Performance Dashboard" },
    {
      name: "description",
      content: "Business Development Performance Dashboard",
    },
  ];
}

export default function Home() {
  const navigate = useNavigate();

  useEffect(() => {
    navigate("/bd-list", { replace: true });
  }, [navigate]);

  return <Loading text="Redirecting to BD Dashboard..." />;
}
