import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

interface Props {
  photoCount: number;
  videoCount: number;
}

export function GalleryHeader({ photoCount, videoCount }: Props) {
  return (
    <SafeAreaView style={styles.header}>
      <Text style={styles.title}>Gallery</Text>
      <Text style={styles.subtitle}>
        {photoCount} photos • {videoCount} videos
      </Text>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    alignItems: "center",
    marginBottom: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: "bold",
    color: "#14B8A6",
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 13,
    color: "#666",
  },
});
