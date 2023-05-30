import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

const moodOptions = [
  { emoji: '🧑‍💻', description: 'studious' },
  { emoji: '🤔', description: 'pensive' },
  { emoji: '😊', description: 'happy' },
  { emoji: '🥳', description: 'celebratory' },
  { emoji: '😤', description: 'frustrated' },
];

export const MoodPicker: React.FC = () => {
  return (
    <View style={styles.moodOptions}>
      {moodOptions.map(options => (
        <Text key={options.emoji}>{options.emoji}</Text>
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  moodOptions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
});
