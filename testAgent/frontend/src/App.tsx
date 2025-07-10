import React, { useState, useEffect } from 'react';
import { Play, Globe, User, Lock, Lightbulb, CheckCircle, XCircle, Clock, AlertCircle, HelpCircle } from 'lucide-react';

// Types based on your backend models
interface ClusterConfig {
  ip: string;
  username: string;
  password: string;
  url: string;
}

interface TestSession {
  sessionId: string;
  status: 'created' | 'parsing' | 'needs_clarification' | 'generating' | 'executing' | 'completed' | 'failed';
  command: string;
  workflows: string[];
  errorMessage?: string;
}

interface ExecutionStep {
  stepId: string;
  workflow: string;
  tddStep: string;
  status: string;
  timestamp: string;
  errorDetails?: string;
}

interface ClarificationOption {
  value: string;
  label: string;
  description?: string;
  data?: any;
}

interface ClarificationQuestion {
  type: string;
  message: string;
  options: ClarificationOption[];
  workflow_context: string;
  parameter_name?: string;
}

const E2ETestingAgent: React.FC = () => {
  const [instruction, setInstruction] = useState('');
  const [clusterConfig, setClusterConfig] = useState<ClusterConfig>({
    ip: '',
    username: '',
    password: '',
    url: ''
  });
  const [isExecuting, setIsExecuting] = useState(false);
  const [testSession, setTestSession] = useState<TestSession | null>(null);
  const [executionSteps, setExecutionSteps] = useState<ExecutionStep[]>([]);
  const [showExamples, setShowExamples] = useState(false);
  
  // Clarification state
  const [showClarification, setShowClarification] = useState(false);
  const [clarificationQuestion, setClarificationQuestion] = useState<ClarificationQuestion | null>(null);
  const [selectedOption, setSelectedOption] = useState<string>('');

  // Example instructions based on your templates
  const exampleInstructions = [
    "create network hierarchy with area 'TestArea' and building 'TestBuilding'",
    "create 3 L3VN for fabric 'TestFabric'",
    "add and provision 5 devices to fabric 'ProductionFabric'",
    "create fabric 'DemoFabric' with network hierarchy and provision devices",
    "login to cluster and verify home page accessibility",
    "create L3VN",  // This will trigger clarification
    "provision devices to existing fabric"  // This might trigger clarification
  ];

  // Enhanced API calls with clarification support
  const executeTest = async () => {
    if (!instruction.trim() || !clusterConfig.ip || !clusterConfig.username) {
      alert('Please fill in all required fields');
      return;
    }

    setIsExecuting(true);
    setTestSession(null);
    setExecutionSteps([]);
    setShowClarification(false);

    try {
      // Step 1: Parse test instructions
      const parseResponse = await fetch('http://localhost:8000/parse_test_instructions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: instruction,
          url: clusterConfig.url || `https://${clusterConfig.ip}`,
          username: clusterConfig.username,
          password: clusterConfig.password
        })
      });

      if (!parseResponse.ok) {
        throw new Error(`Failed to parse instructions: ${parseResponse.statusText}`);
      }

      const parseResult = await parseResponse.json();
      console.log('Parse result:', parseResult);
      
      // Step 2: Check if clarification is needed
      if (parseResult.status === 'needs_clarification') {
        console.log('Clarification needed:', parseResult.clarification);
        
        // Show clarification dialog
        setClarificationQuestion(parseResult.clarification);
        setShowClarification(true);
        setTestSession({
          sessionId: parseResult.session_id,
          status: 'needs_clarification',
          command: instruction,
          workflows: parseResult.detected_workflows || [],
        });
        setIsExecuting(false);
        return; // Wait for user clarification
      }
      
      // Step 3: No clarification needed, proceed with execution
      await proceedWithExecution(parseResult.session_id, parseResult);
      
    } catch (error) {
      console.error('Execution error:', error);
      setTestSession({
        sessionId: 'error',
        status: 'failed',
        command: instruction,
        workflows: [],
        errorMessage: error instanceof Error ? error.message : 'Unknown error occurred'
      });
      setIsExecuting(false);
    }
  };

  const handleClarificationResponse = async () => {
    if (!selectedOption || !testSession || !clarificationQuestion) {
      alert('Please select an option');
      return;
    }

    setIsExecuting(true);
    
    try {
      // Send clarification response
      const clarificationResponse = await fetch('http://localhost:8000/api/v1/provide_clarification', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: testSession.sessionId,
          clarification_response: {
            type: clarificationQuestion.type,
            choice: selectedOption
          }
        })
      });

      if (!clarificationResponse.ok) {
        throw new Error(`Failed to process clarification: ${clarificationResponse.statusText}`);
      }

      const clarificationResult = await clarificationResponse.json();
      console.log('Clarification result:', clarificationResult);

      // Hide clarification dialog
      setShowClarification(false);
      setClarificationQuestion(null);
      setSelectedOption('');

      // Update session with resolved workflows
      setTestSession(prev => ({
        ...prev!,
        status: 'parsing',
        workflows: clarificationResult.updated_workflows,
      }));

      // Proceed with execution
      await proceedWithExecution(testSession.sessionId, clarificationResult);
      
    } catch (error) {
      console.error('Clarification error:', error);
      setTestSession(prev => ({
        ...prev!,
        status: 'failed',
        errorMessage: error instanceof Error ? error.message : 'Clarification failed'
      }));
      setIsExecuting(false);
      setShowClarification(false);
    }
  };

  const skipClarification = async () => {
    if (!testSession) return;

    setIsExecuting(true);
    
    try {
      const skipResponse = await fetch(`http://localhost:8000/api/v1/session/${testSession.sessionId}/skip_clarification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!skipResponse.ok) {
        throw new Error(`Failed to skip clarification: ${skipResponse.statusText}`);
      }

      const skipResult = await skipResponse.json();
      console.log('Skip result:', skipResult);

      // Hide clarification dialog
      setShowClarification(false);
      setClarificationQuestion(null);

      // Update session
      setTestSession(prev => ({
        ...prev!,
        status: 'parsing',
        workflows: skipResult.workflows,
      }));

      // Proceed with execution
      await proceedWithExecution(testSession.sessionId, skipResult);
      
    } catch (error) {
      console.error('Skip clarification error:', error);
      setTestSession(prev => ({
        ...prev!,
        status: 'failed',
        errorMessage: error instanceof Error ? error.message : 'Skip clarification failed'
      }));
      setIsExecuting(false);
      setShowClarification(false);
    }
  };

  const proceedWithExecution = async (sessionId: string, parseResult: any) => {
    try {
      // Execute the test plan
      const sessionResponse = await fetch('http://localhost:8000/execute_test_plan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId
        })
      });

      if (!sessionResponse.ok) {
        throw new Error(`Failed to execute test: ${sessionResponse.statusText}`);
      }

      const sessionResult = await sessionResponse.json();
      console.log('Session result:', sessionResult);
      
      // Update UI with initial session info
      setTestSession({
        sessionId: sessionId,
        status: 'executing',
        command: instruction,
        workflows: parseResult.workflows || parseResult.updated_workflows || [],
        errorMessage: undefined
      });

      // Start polling for execution status
      pollExecutionStatus(sessionId);

    } catch (error) {
      console.error('Execution error:', error);
      setTestSession({
        sessionId: sessionId,
        status: 'failed',
        command: instruction,
        workflows: [],
        errorMessage: error instanceof Error ? error.message : 'Execution failed'
      });
      setIsExecuting(false);
    }
  };

  const pollExecutionStatus = async (sessionId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch('http://localhost:8000/get_session_status', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            session_id: sessionId
          })
        });
        
        if (response.ok) {
          const status = await response.json();
          console.log('Status update:', status);
          setTestSession(prev => ({
            ...prev!,
            sessionId: sessionId,
            status: status.status || 'executing',
            command: instruction,
            workflows: status.workflows || prev?.workflows || [],
            errorMessage: status.error_message
          }));
          
          // Stop polling when test is complete
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(interval);
            setIsExecuting(false);
            if (status.steps) {
              setExecutionSteps(status.steps);
            }
          }
        }
      } catch (error) {
        console.error('Status polling error:', error);
        clearInterval(interval);
        setIsExecuting(false);
      }
    }, 3000); // Poll every 3 seconds

    // Cleanup after 10 minutes
    setTimeout(() => {
      clearInterval(interval);
      setIsExecuting(false);
    }, 600000);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed': return <XCircle className="w-5 h-5 text-red-500" />;
      case 'executing': case 'generating': return <Clock className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'needs_clarification': return <HelpCircle className="w-5 h-5 text-orange-500" />;
      default: return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-50 border-green-200 text-green-800';
      case 'failed': return 'bg-red-50 border-red-200 text-red-800';
      case 'needs_clarification': return 'bg-orange-50 border-orange-200 text-orange-800';
      case 'executing': case 'parsing': case 'generating': return 'bg-blue-50 border-blue-200 text-blue-800';
      default: return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-slate-800 mb-2">
            E2E Testing Agent
          </h1>
          <p className="text-slate-600 text-lg">
            Transform natural language commands into automated Playwright tests
          </p>
        </div>

        {/* Main Interface */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-6">
          {/* Test Instruction Input */}
          <div className="mb-8">
            <label className="block text-sm font-semibold text-slate-700 mb-3">
              Test Instruction
            </label>
            <div className="relative">
              <textarea
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="Describe what you want to test in natural language..."
                className="w-full h-32 px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-slate-700"
                disabled={isExecuting}
              />
              <button
                onClick={() => setShowExamples(!showExamples)}
                className="absolute top-3 right-3 p-2 text-slate-400 hover:text-slate-600 transition-colors"
                title="Show examples"
              >
                <Lightbulb className="w-5 h-5" />
              </button>
            </div>
            
            {/* Examples */}
            {showExamples && (
              <div className="mt-4 p-4 bg-slate-50 rounded-lg border border-slate-200">
                <h4 className="text-sm font-semibold text-slate-700 mb-3">Example Instructions:</h4>
                <div className="space-y-2">
                  {exampleInstructions.map((example, index) => (
                    <button
                      key={index}
                      onClick={() => {
                        setInstruction(example);
                        setShowExamples(false);
                      }}
                      className="block w-full text-left p-2 text-sm text-slate-600 hover:bg-white hover:text-slate-800 rounded transition-colors"
                    >
                      {example}
                      {example.includes('create L3VN') && (
                        <span className="text-xs text-orange-600 ml-2">(needs clarification)</span>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Cluster Configuration */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-slate-700 mb-4">Cluster Configuration</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-600 mb-2">
                  <Globe className="w-4 h-4 inline mr-1" />
                  Cluster IP *
                </label>
                <input
                  type="text"
                  value={clusterConfig.ip}
                  onChange={(e) => setClusterConfig(prev => ({ ...prev, ip: e.target.value }))}
                  placeholder="192.168.1.100"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={isExecuting}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-600 mb-2">
                  Base URL (optional)
                </label>
                <input
                  type="text"
                  value={clusterConfig.url}
                  onChange={(e) => setClusterConfig(prev => ({ ...prev, url: e.target.value }))}
                  placeholder="https://cluster.example.com"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={isExecuting}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-600 mb-2">
                  <User className="w-4 h-4 inline mr-1" />
                  Username *
                </label>
                <input
                  type="text"
                  value={clusterConfig.username}
                  onChange={(e) => setClusterConfig(prev => ({ ...prev, username: e.target.value }))}
                  placeholder="admin"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={isExecuting}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-600 mb-2">
                  <Lock className="w-4 h-4 inline mr-1" />
                  Password *
                </label>
                <input
                  type="password"
                  value={clusterConfig.password}
                  onChange={(e) => setClusterConfig(prev => ({ ...prev, password: e.target.value }))}
                  placeholder="••••••••"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={isExecuting}
                />
              </div>
            </div>
          </div>

          {/* Execute Button */}
          <div className="text-center">
            <button
              onClick={executeTest}
              disabled={isExecuting || !instruction.trim() || !clusterConfig.ip || !clusterConfig.username}
              className="inline-flex items-center px-8 py-4 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 disabled:transform-none"
            >
              <Play className="w-5 h-5 mr-2" />
              {isExecuting ? 'Executing Test...' : 'Execute Test'}
            </button>
          </div>
        </div>

        {/* Clarification Dialog */}
        {showClarification && clarificationQuestion && (
          <div className="bg-white rounded-xl shadow-lg p-6 mb-6 border-l-4 border-orange-500">
            <div className="flex items-center mb-4">
              <HelpCircle className="w-6 h-6 text-orange-500 mr-2" />
              <h3 className="text-lg font-semibold text-slate-700">Clarification Needed</h3>
            </div>
            
            <p className="text-slate-600 mb-4">{clarificationQuestion.message}</p>
            
            <div className="space-y-3 mb-6">
              {clarificationQuestion.options.map((option, index) => (
                <label key={option.value} className="flex items-start space-x-3 cursor-pointer">
                  <input
                    type="radio"
                    name="clarification"
                    value={option.value}
                    checked={selectedOption === option.value}
                    onChange={(e) => setSelectedOption(e.target.value)}
                    className="mt-1 text-blue-600 focus:ring-blue-500"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-slate-700">{option.label}</div>
                    {option.description && (
                      <div className="text-sm text-slate-500 mt-1">{option.description}</div>
                    )}
                  </div>
                </label>
              ))}
            </div>
            
            <div className="flex space-x-3">
              <button
                onClick={handleClarificationResponse}
                disabled={!selectedOption || isExecuting}
                className="flex-1 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {isExecuting ? 'Processing...' : 'Continue'}
              </button>
              <button
                onClick={skipClarification}
                disabled={isExecuting}
                className="px-4 py-2 bg-gray-200 text-gray-700 font-medium rounded-lg hover:bg-gray-300 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors"
              >
                Use Defaults
              </button>
            </div>
          </div>
        )}

        {/* Test Results */}
        {testSession && (
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="text-lg font-semibold text-slate-700 mb-4">Test Execution Results</h3>
            
            {/* Status */}
            <div className={`p-4 rounded-lg border mb-4 ${getStatusColor(testSession.status)}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  {getStatusIcon(testSession.status)}
                  <span className="ml-2 font-medium capitalize">
                    {testSession.status.replace('_', ' ')}
                  </span>
                </div>
                <span className="text-sm">Session: {testSession.sessionId}</span>
              </div>
              {testSession.errorMessage && (
                <div className="mt-2 text-sm">
                  <AlertCircle className="w-4 h-4 inline mr-1" />
                  {testSession.errorMessage}
                </div>
              )}
            </div>

            {/* Command */}
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-slate-600 mb-2">Command Executed:</h4>
              <div className="p-3 bg-slate-50 rounded border text-sm text-slate-700">
                {testSession.command}
              </div>
            </div>

            {/* Workflows */}
            {testSession.workflows && testSession.workflows.length > 0 && (
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-slate-600 mb-2">Detected Workflows:</h4>
                <div className="flex flex-wrap gap-2">
                  {testSession.workflows.map((workflow, index) => (
                    <span key={index} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                      {workflow.replace('_', ' ')}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Execution Steps */}
            {executionSteps.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-slate-600 mb-2">Execution Steps:</h4>
                <div className="space-y-2">
                  {executionSteps.map((step, index) => (
                    <div key={index} className="p-3 border border-slate-200 rounded">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{step.workflow}</span>
                        <span className={`px-2 py-1 rounded text-xs ${getStatusColor(step.status)}`}>
                          {step.status}
                        </span>
                      </div>
                      <div className="text-sm text-slate-600 mt-1">{step.tddStep}</div>
                      {step.errorDetails && (
                        <div className="text-sm text-red-600 mt-1">{step.errorDetails}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-8 text-sm text-slate-500">
          <p>E2E Testing Agent - Intelligent test automation with natural language commands</p>
        </div>
      </div>
    </div>
  );
};

export default E2ETestingAgent;