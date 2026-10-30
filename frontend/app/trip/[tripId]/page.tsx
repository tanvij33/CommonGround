import { redirect } from "next/navigation";

export default function TripIdIndexPage({ params }: { params: { tripId: string } }) {
  redirect(`/trip/${params.tripId}/plan`);
}
