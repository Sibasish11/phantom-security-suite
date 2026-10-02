import type { Agent, Domain } from './api';

// Presentation only: ownership is still enforced by the API. Bank session IDs
// identify the registered agent, so its tenant-visible domain can be displayed
// without inventing an incident field or choosing an unrelated first domain.
export function bankSessionDomain(sessionId: string, agents: Agent[], domains: Domain[]): Domain | undefined {
  const [kind, agentId] = sessionId.split(':');
  if (kind !== 'bank' || !agentId) return undefined;
  const agent = agents.find(item => item.agent_id === agentId);
  return agent ? domains.find(domain => domain.id === agent.domain_id) : undefined;
}
