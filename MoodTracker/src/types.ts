export type MoodOptionType = {
  emoji: string;
  description: string;
};

export type MoodOptionsWithTimestamp = {
  mood: MoodOptionType;
  timestamp: number;
};
