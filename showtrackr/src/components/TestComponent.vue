<template>
    <div class="p-6 rounded-lg shadow-md">
      <h2 class="text-2xl font-bold text-primary mb-4">Setup Test</h2>
      
      <div class="mb-4">
        <h3 class="text-lg font-semibold mb-2">Tailwind Test</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="bg-primary text-white p-4 rounded">
            Primary Color Block
          </div>
          <div class="bg-secondary text-white p-4 rounded">
            Secondary Color Block
          </div>
        </div>
      </div>
      
      <div class="mt-6">
        <h3 class="text-lg font-semibold mb-2">PrimeVue Test</h3>
        <Button label="PrimeVue Button" class="mr-2" />
        <InputText v-model="inputValue" placeholder="Type here..." class="mr-2" />
        <Dropdown v-model="selected" :options="options" optionLabel="name" placeholder="Select" class="w-48" />
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref } from 'vue';
  import Button from 'primevue/button';
  import InputText from 'primevue/inputtext';
  import Dropdown from 'primevue/dropdown';
  
  const inputValue = ref('');
  const selected = ref(null);
  const options = ref([
    { name: 'Option 1', value: 1 },
    { name: 'Option 2', value: 2 },
    { name: 'Option 3', value: 3 }
  ]);
  </script>