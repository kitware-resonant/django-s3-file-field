<template>
  <div>
    <JoistUpload />
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import JoistUpload from '@/components/JoistUpload.vue';

@Component({
  components: {
    JoistUpload,
  },
})
export default class App extends Vue {}
</script>
