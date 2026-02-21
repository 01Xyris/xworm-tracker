fetch('/api/graph_data')
    .then(response => response.json())
    .then(data => {
        const container = document.getElementById('graph');
        const loading = document.getElementById('loading');
        
        const nodes = new vis.DataSet(data.nodes.map(node => ({
            id: node.id,
            label: node.label,
            color: {
                background: node.group === 'ip' ? '#6b588a' : '#2a2a2a',
                border: '#555',
                highlight: {
                    background: node.group === 'ip' ? '#7b68a8' : '#3a3a3a',
                    border: '#7b68a8'
                },
                hover: {
                    background: node.group === 'ip' ? '#7b68a8' : '#3a3a3a',
                    border: '#888'
                }
            },
            font: { 
                color: '#d0d0d0',
                size: 11,
                face: 'MS Sans Serif, Microsoft Sans Serif, sans-serif'
            },
            shape: 'box',
            borderWidth: 2,
            shadow: false
        })));
        
        const edges = new vis.DataSet(data.edges.map(edge => ({
            from: edge.from,
            to: edge.to,
            color: {
                color: '#555',
                highlight: '#7b68a8',
                hover: '#7b68a8'
            },
            width: 1,
            shadow: false
        })));
        
        const graphData = { nodes: nodes, edges: edges };
        
        const options = {
            nodes: {
                borderWidth: 2,
                borderWidthSelected: 2,
                font: { 
                    size: 11,
                    color: '#d0d0d0',
                    face: 'MS Sans Serif, Microsoft Sans Serif, sans-serif'
                },
                shadow: false
            },
            edges: {
                width: 1,
                smooth: { 
                    type: 'continuous' 
                },
                shadow: false
            },
            physics: {
                barnesHut: {
                    gravitationalConstant: -8000,
                    springConstant: 0.001,
                    springLength: 200
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 100,
                hideEdgesOnDrag: true
            }
        };
        
        new vis.Network(container, graphData, options);
        
        loading.style.display = 'none';
        container.style.display = 'block';
    })
    .catch(error => {
        const loading = document.getElementById('loading');
        loading.innerHTML = '<div style="font-size: 14px; font-weight: bold; margin-bottom: 10px; color: #808080;">Failed to load graph</div><div style="font-size: 11px; color: #808080;">Error loading data</div>';
    });