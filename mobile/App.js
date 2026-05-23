import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text } from 'react-native';
import EventsScreen from './screens/EventsScreen';
import NewsScreen from './screens/NewsScreen';

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={{
          headerStyle: { backgroundColor: '#111111' },
          headerTintColor: '#FFFFFF',
          headerTitleStyle: { fontWeight: 'bold', letterSpacing: 4 },
          tabBarStyle: { backgroundColor: '#111111', borderTopColor: '#222222' },
          tabBarActiveTintColor: '#E8272A',
          tabBarInactiveTintColor: '#666666',
        }}
      >
        <Tab.Screen
          name="FIGHTS"
          component={EventsScreen}
          options={{ tabBarLabel: 'FIGHTS', title: 'CUTMAN' }}
        />
        <Tab.Screen
          name="NEWS"
          component={NewsScreen}
          options={{ tabBarLabel: 'NEWS', title: 'CUTMAN' }}
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
}