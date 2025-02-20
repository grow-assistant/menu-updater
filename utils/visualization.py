"""Visualization components for menu analytics"""
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any
import streamlit as st

def render_order_frequency_chart(data: List[Dict[str, Any]]) -> go.Figure:
    """Render order frequency chart"""
    if not data:
        return None
    
    fig = px.bar(
        data,
        x='name',
        y='orders',
        title='Most Popular Items',
        labels={'name': 'Item Name', 'orders': 'Number of Orders'},
        color='revenue',
        hover_data=['price', 'revenue']
    )
    fig.update_layout(
        xaxis_title="Item Name",
        yaxis_title="Number of Orders",
        showlegend=True
    )
    return fig

def render_time_patterns_chart(patterns: List[Dict[str, Any]]) -> go.Figure:
    """Render time-based patterns chart"""
    if not patterns:
        return None
    
    # Convert time ranges to readable format
    for p in patterns:
        start = str(p['time_range']).split('-')[0]
        end = str(p['time_range']).split('-')[1]
        p['start'] = f"{start[:2]}:{start[2:]}"
        p['end'] = f"{end[:2]}:{end[2:]}"
    
    fig = px.timeline(
        patterns,
        x_start='start',
        x_end='end',
        y='category',
        title='Category Time Ranges',
        color='orders',
        hover_data=['items']
    )
    fig.update_layout(
        xaxis_title="Time of Day",
        yaxis_title="Category",
        showlegend=True
    )
    return fig

def render_category_relationships(relationships: Dict[str, List[Dict[str, Any]]]) -> go.Figure:
    """Render category relationship diagram"""
    if not relationships:
        return None
    
    # Prepare nodes and links for Sankey diagram
    nodes = []
    links = []
    node_ids = {}
    
    # Create nodes
    for cat1 in relationships:
        if cat1 not in node_ids:
            node_ids[cat1] = len(nodes)
            nodes.append(cat1)
        
        for rel in relationships[cat1]:
            cat2 = rel['category']
            if cat2 not in node_ids:
                node_ids[cat2] = len(nodes)
                nodes.append(cat2)
            
            links.append({
                'source': node_ids[cat1],
                'target': node_ids[cat2],
                'value': rel['frequency']
            })
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=nodes,
            color="blue"
        ),
        link=dict(
            source=[link['source'] for link in links],
            target=[link['target'] for link in links],
            value=[link['value'] for link in links]
        )
    )])
    
    fig.update_layout(
        title_text="Category Relationships",
        font_size=10
    )
    return fig

def render_analytics_dashboard(connection, location_id: int):
    """Render complete analytics dashboard"""
    from utils.menu_analytics import (
        get_popular_items,
        analyze_time_patterns,
        get_category_relationships
    )
    
    st.title("📊 Menu Analytics Dashboard")
    
    # Popular items chart
    st.subheader("🔥 Popular Items")
    with st.spinner("Loading order data..."):
        items_data = get_popular_items(connection, location_id)
        if items_fig := render_order_frequency_chart(items_data):
            st.plotly_chart(items_fig, use_container_width=True)
        else:
            st.info("No order data available")
    
    # Time patterns chart
    st.subheader("⏰ Time-based Patterns")
    with st.spinner("Analyzing time patterns..."):
        patterns_data = analyze_time_patterns(connection, location_id)
        if 'time_based_categories' in patterns_data:
            if patterns_fig := render_time_patterns_chart(patterns_data['time_based_categories']):
                st.plotly_chart(patterns_fig, use_container_width=True)
            else:
                st.info("No time pattern data available")
    
    # Category relationships
    st.subheader("🔗 Category Relationships")
    with st.spinner("Loading relationship data..."):
        relationships = get_category_relationships(connection, location_id)
        if relationships_fig := render_category_relationships(relationships):
            st.plotly_chart(relationships_fig, use_container_width=True)
        else:
            st.info("No relationship data available")
