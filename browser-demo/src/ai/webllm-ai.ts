/**
 * Optional WebLLM-powered AI for creative NPC behavior.
 *
 * Uses dynamic imports so the ~2GB model is only loaded if the user opts in.
 * Requires a browser with WebGPU support.
 */

import type { Entity, GameState, Action } from '../core/types';
import { ALIGNMENT_INFO, getWeightsForAlignment } from '../core/alignment';

export function isWebGPUAvailable(): boolean {
  return 'gpu' in navigator;
}

interface WebLLMEngine {
  chat: {
    completions: {
      create: (params: {
        messages: { role: string; content: string }[];
      }) => Promise<{ choices: { message: { content: string } }[] }>;
    };
  };
}

export class WebLLMAI {
  private engine: WebLLMEngine | null = null;
  private _loading = false;
  private loadError: string | null = null;

  async initialize(
    onProgress?: (progress: number, status: string) => void,
  ): Promise<boolean> {
    if (this.engine) return true;
    if (this._loading) return false;

    this._loading = true;

    try {
      const { CreateMLCEngine } = await import('@mlc-ai/web-llm');
      this.engine = (await CreateMLCEngine(
        'Phi-3-mini-4k-instruct-q4f16_1-MLC',
        {
          initProgressCallback: (report: { progress: number; text: string }) => {
            onProgress?.(report.progress, report.text);
          },
        },
      )) as unknown as WebLLMEngine;

      this._loading = false;
      return true;
    } catch (error) {
      this.loadError =
        error instanceof Error ? error.message : 'Unknown error';
      this._loading = false;
      return false;
    }
  }

  isAvailable(): boolean {
    return this.engine !== null;
  }

  isLoading(): boolean {
    return this._loading;
  }

  getError(): string | null {
    return this.loadError;
  }

  async chooseAction(entity: Entity, state: GameState): Promise<Action> {
    if (!this.engine) {
      throw new Error('WebLLM not initialized');
    }

    const systemPrompt = this.getSystemPrompt(entity);
    const userPrompt = this.buildPrompt(entity, state);

    const response = await this.engine.chat.completions.create({
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
    });

    const text = response.choices[0]?.message?.content ?? '';
    return this.parseResponse(text, entity, state);
  }

  private getSystemPrompt(entity: Entity): string {
    const info = ALIGNMENT_INFO[entity.alignment];
    const weights = getWeightsForAlignment(entity.alignment);

    const traits: string[] = [];
    if (weights.aggression > 0.7) traits.push('aggressive');
    if (weights.allyProtection > 0.7) traits.push('protective');
    if (weights.mercy < 0.3) traits.push('ruthless');
    if (weights.fleeThreshold > 0.5) traits.push('cautious');

    return (
      `You are a ${info.name} ${info.archetype}. "${info.tagline}"\n` +
      `Style: ${traits.join(', ') || 'balanced'}\n` +
      'Reply with ONLY: ACTION: <attack|move|defend|flee> TARGET: <name or none>'
    );
  }

  private buildPrompt(entity: Entity, state: GameState): string {
    const enemies = Array.from(state.entities.values())
      .filter((e) => e.type !== entity.type && e.hp > 0)
      .map((e) => `${e.name}(${e.hp}hp)`)
      .join(', ');

    const allies =
      Array.from(state.entities.values())
        .filter(
          (e) => e.type === entity.type && e.id !== entity.id && e.hp > 0,
        )
        .map((e) => `${e.name}(${e.hp}hp)`)
        .join(', ') || 'none';

    return (
      `You: ${entity.name}, ${entity.hp}/${entity.maxHp}hp\n` +
      `Enemies: ${enemies}\n` +
      `Allies: ${allies}\n` +
      'Choose ONE action.'
    );
  }

  private parseResponse(
    response: string,
    entity: Entity,
    state: GameState,
  ): Action {
    const actionMatch = response.match(/ACTION:\s*(\w+)/i);
    const targetMatch = response.match(/TARGET:\s*(\w+)/i);

    const actionType = actionMatch?.[1]?.toLowerCase();
    const targetName = targetMatch?.[1];

    if (actionType === 'attack' && targetName) {
      const target = Array.from(state.entities.values()).find((e) =>
        e.name.toLowerCase().includes(targetName.toLowerCase()),
      );
      if (target) {
        return { type: 'attack', actor: entity.id, target: target.id };
      }
    }

    if (actionType === 'flee') {
      return { type: 'flee', actor: entity.id };
    }

    if (actionType === 'defend') {
      return { type: 'defend', actor: entity.id };
    }

    return { type: 'end_turn', actor: entity.id };
  }
}
