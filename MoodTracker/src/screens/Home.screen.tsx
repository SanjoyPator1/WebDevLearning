import React from 'react';
import { View, StyleSheet } from 'react-native';
import { MoodPicker } from '../components/MoodPicker';

export const Home: React.FC = () => {
  return (
    <View style={styles.container}>
      <MoodPicker />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 20,
  },
});
