import { StyleSheet, Text, View, FlatList, ActivityIndicator } from 'react-native';
import { useState, useEffect } from 'react';

const API = 'http://192.168.1.250:8000';

export default function NewsScreen() {
    const [ articles, setArticles ] = useState([]);
    const [ loading, setLoading ] = useState(true);

    useEffect(() => {
        fetch(`${API}/api/news`)
            .then(res => res.json())
            .then(data => {
              setArticles(data);
              setLoading(false);
            });
    }, []);

    if (loading) {
        return (
            <View style ={styles.container}>
              <ActivityIndicator size="large" color="#E8272A" />
            </View>
        );
    }

    return (
        <FlatList
          style={styles.container}
          data={articles}
          keyExtractor={(item, index) => index.toString()}
          renderItem={({ item }) => (
            <View style={styles.eventRow}>
              <Text style={styles.eventPromo}>{item.source}</Text>

              <Text style={styles.eventName}>{item.title}</Text>
              <Text style={styles.eventDate}>{new Date(item.published).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</Text>
            </View>
        )}
    />
    );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#111111',
  },
eventRow: {
  paddingHorizontal: 16,
  paddingVertical: 12,
  borderBottomWidth: 1,
  borderBottomColor: '#222222',
},
eventPromo: {
  fontSize: 11,
  color: '#E8272A',
  fontWeight: 'bold',
  marginTop: 2,
},
eventName: {
  fontSize: 16,
  color: '#FFFFFF',
    fontWeight: 'bold',
    marginTop: 2,
},
eventDate: {
  fontSize: 13,
  color: '#888888',
  marginTop: 2, 
},
});