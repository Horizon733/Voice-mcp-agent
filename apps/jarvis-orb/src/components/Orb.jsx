import EnergySphere from "./EnergySphere";
import Particles from "./Particles";

export default function Orb({ audioLevel = 0 }) {
  return (
    <>
      <Particles audioLevel={audioLevel} />
      <EnergySphere audioLevel={audioLevel} />
    </>
  );
}