/**
 * The single API entry point. VITE_USE_MOCKS=true (default) runs everything on the
 * bundled fictional data. With VITE_USE_MOCKS=false, EventSim resources go live
 * through the dev proxy; gateway-side resources stay on mocks until the gateway
 * exposes them, and `api.source` tells pages which is which.
 */
import { liveAttendees, liveEvents, livePartners, liveSessions, liveSpeakers } from './live';
import {
  mockApprovals,
  mockAttacks,
  mockAttendees,
  mockAudit,
  mockConversations,
  mockEvents,
  mockGateway,
  mockPartners,
  mockResults,
  mockSessions,
  mockSpeakers,
  mockToolCalls,
} from './mock';
import type { Api } from './types';

export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== 'false';

export const api: Api = {
  events: USE_MOCKS ? mockEvents : liveEvents,
  sessions: USE_MOCKS ? mockSessions : liveSessions,
  speakers: USE_MOCKS ? mockSpeakers : liveSpeakers,
  partners: USE_MOCKS ? mockPartners : livePartners,
  attendees: USE_MOCKS ? mockAttendees : liveAttendees,
  conversations: mockConversations,
  toolCalls: mockToolCalls,
  approvals: mockApprovals,
  audit: mockAudit,
  gateway: mockGateway,
  attacks: mockAttacks,
  results: mockResults,
  source: {
    events: USE_MOCKS ? 'mock' : 'live',
    sessions: USE_MOCKS ? 'mock' : 'live',
    speakers: USE_MOCKS ? 'mock' : 'live',
    partners: USE_MOCKS ? 'mock' : 'live',
    attendees: USE_MOCKS ? 'mock' : 'live',
    conversations: 'mock',
    toolCalls: 'mock',
    approvals: 'mock',
    audit: 'mock',
    gateway: 'mock',
    attacks: 'mock',
    results: 'mock',
  },
};

export * from './types';
