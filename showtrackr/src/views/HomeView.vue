<template>
  <div class="w-full">
    <h1 class="text-3xl font-bold text-center mb-8">ShowTrackr Setup Test</h1>
    
    <!-- Tailwind Test Section -->
    <div class="bg-gradient-to-r from-blue-500 to-purple-600 p-8 rounded-lg shadow-lg mb-8">
      <h2 class="text-white text-2xl font-bold mb-4">Tailwind CSS Test</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-white p-4 rounded-lg shadow hover:shadow-xl transition-shadow duration-300">
          <p class="text-gray-800 font-medium">Card 1</p>
          <p class="text-gray-600 text-sm mt-2">If you can see this card with styling, Tailwind is working!</p>
        </div>
        <div class="bg-primary p-4 rounded-lg shadow text-white">
          <p class="font-medium">Card 2</p>
          <p class="text-sm mt-2">This uses our custom primary color from Tailwind config</p>
        </div>
        <div class="bg-secondary p-4 rounded-lg shadow text-white">
          <p class="font-medium">Card 3</p>
          <p class="text-sm mt-2">This uses our custom secondary color from Tailwind config</p>
        </div>
      </div>
      <div class="mt-4 flex gap-4 justify-center">
        <button class="btn btn-primary">Primary Button</button>
        <button class="btn bg-secondary text-white">Secondary Button</button>
      </div>
    </div>
    
    <!-- PrimeVue Test Section -->
    <div class="bg-gray-100 dark:bg-gray-800 p-8 rounded-lg shadow-lg mb-8">
      <h2 class="text-2xl font-bold mb-4">PrimeVue Components Test</h2>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="space-y-4">
          <h3 class="text-xl font-semibold">Basic Components</h3>
          
          <div class="space-y-2">
            <label class="block text-sm font-medium">Button Component</label>
            <div class="flex flex-wrap gap-2">
              <Button label="Primary" />
              <Button label="Secondary" severity="secondary" />
              <Button label="Success" severity="success" />
              <Button label="Info" severity="info" />
              <Button label="Warning" severity="warning" />
              <Button label="Help" severity="help" />
              <Button label="Danger" severity="danger" />
            </div>
          </div>
          
          <div class="space-y-2">
            <label class="block text-sm font-medium">Input Component</label>
            <InputText v-model="inputValue" placeholder="Type something..." class="w-full" />
            <small class="block mt-1">Input value: {{ inputValue }}</small>
          </div>
          
          <div class="space-y-2">
            <label class="block text-sm font-medium">Checkbox Component</label>
            <div class="flex items-center gap-2">
              <Checkbox v-model="checked" :binary="true" inputId="binary" />
              <label for="binary">{{ checked ? 'Checked' : 'Unchecked' }}</label>
            </div>
          </div>
        </div>
        
        <div class="space-y-4">
          <h3 class="text-xl font-semibold">Advanced Components</h3>
          
          <div class="space-y-2">
            <label class="block text-sm font-medium">Calendar Component</label>
            <Calendar v-model="date" showIcon class="w-full" />
          </div>
          
          <div class="space-y-2">
            <label class="block text-sm font-medium">Dropdown Component</label>
            <Dropdown 
              v-model="selectedCity" 
              :options="cities" 
              optionLabel="name" 
              placeholder="Select a City" 
              class="w-full"
            />
          </div>
          
          <div class="space-y-2">
            <label class="block text-sm font-medium">Toast Message</label>
            <Button 
              label="Show Toast" 
              icon="pi pi-check" 
              @click="showToast" 
            />
          </div>
        </div>
      </div>
    </div>
    
    <!-- Additional Test Components -->
    <div class="bg-white dark:bg-gray-900 p-8 rounded-lg shadow-lg">
      <h2 class="text-2xl font-bold mb-4">Dark Mode Test</h2>
      <p class="mb-4">This section tests the dark mode functionality. Toggle dark mode in the header to see changes.</p>
      
      <div class="flex justify-center">
        <Card class="w-full max-w-md">
          <template #header>
            <img alt="Card header image" src="https://primefaces.org/cdn/primevue/images/usercard.png" />
          </template>
          <template #title>
            Dark Mode Compatible Card
          </template>
          <template #content>
            <p>This PrimeVue card should adopt your theme's dark mode settings when toggled.</p>
          </template>
          <template #footer>
            <Button icon="pi pi-check" label="Save" />
            <Button icon="pi pi-times" label="Cancel" severity="secondary" style="margin-left: 0.5rem" />
          </template>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useToast } from 'primevue/usetoast';

// PrimeVue components
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Checkbox from 'primevue/checkbox';
import Calendar from 'primevue/calendar';
import Dropdown from 'primevue/dropdown';
import Card from 'primevue/card';

// Setup state
const inputValue = ref('');
const checked = ref(false);
const date = ref(new Date());
const selectedCity = ref(null);
const cities = ref([
  { name: 'New York', code: 'NY' },
  { name: 'London', code: 'LDN' },
  { name: 'Paris', code: 'PRS' },
  { name: 'Tokyo', code: 'TKY' }
]);

// Toast functionality
const toast = useToast();

const showToast = () => {
  toast.add({
    severity: 'success',
    summary: 'Success',
    detail: 'PrimeVue Toast is working!',
    life: 3000
  });
};
</script>