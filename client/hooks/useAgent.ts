import { useContext } from "react";
import { AgentContext } from "../components/agent/AgentProvider";

export const useAgent = () => {
  const context = useContext(AgentContext);
  if (context === undefined) {
    throw new Error("useAgent must be used within an AgentProvider");
  }
  return context;
};

export default useAgent;
