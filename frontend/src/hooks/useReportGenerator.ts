import { useState } from 'react';
import api from '../utils/api';
import { useMachine } from '../contexts/MachineContext';

export function useReportGenerator() {
  const [isGenerating, setIsGenerating] = useState(false);
  const { activeMachine, timeRange } = useMachine();

  const generateReport = async () => {
    if (!activeMachine) return;
    setIsGenerating(true);
    
    try {
      // Add 'Z' to timestamps if they don't have it to ensure UTC mapping in backend
      const start = (timeRange.start.endsWith('Z') || timeRange.start.includes('+')) ? timeRange.start : `${timeRange.start}Z`;
      const end = (timeRange.end.endsWith('Z') || timeRange.end.includes('+')) ? timeRange.end : `${timeRange.end}Z`;
      
      const response = await api.get('/api/reports/generate_pdf', {
        params: {
          machine_id: activeMachine.machine_id,
          start_time: start,
          end_time: end
        },
        responseType: 'blob'
      });

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Report_${activeMachine.machine_id}_${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      window.URL.revokeObjectURL(url);
      link.remove();
    } catch (error: any) {
      console.error("Report generation failed:", error);
      alert(`Failed to generate report: ${error.message || error}`);
    } finally {
      setIsGenerating(false);
    }
  };

  return {
    isGenerating,
    generateReport
  };
}
